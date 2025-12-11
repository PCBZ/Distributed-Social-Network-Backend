"""
CloudWatch Metrics Collection Script for Autoscaling Analysis
Collects ECS, ALB, and DynamoDB metrics during load testing
"""

import boto3
import json
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import argparse
import sys


class CloudWatchMetricsCollector:
    def __init__(self, region='us-west-2'):
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.ecs = boto3.client('ecs', region_name=region)

    def get_ecs_metrics(self, service_name, cluster_name, start_time, end_time, period=60):
        """
        Collect ECS service metrics
        """
        metrics = {}

        # Metric definitions
        metric_configs = [
            {
                'name': 'CPUUtilization',
                'stat': ['Average', 'Maximum'],
                'unit': 'Percent'
            },
            {
                'name': 'MemoryUtilization',
                'stat': ['Average', 'Maximum'],
                'unit': 'Percent'
            }
        ]

        for config in metric_configs:
            for stat in config['stat']:
                try:
                    response = self.cloudwatch.get_metric_statistics(
                        Namespace='AWS/ECS',
                        MetricName=config['name'],
                        Dimensions=[
                            {'Name': 'ServiceName', 'Value': service_name},
                            {'Name': 'ClusterName', 'Value': cluster_name}
                        ],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=period,
                        Statistics=[stat]
                    )

                    key = f"{config['name']}_{stat}"
                    metrics[key] = sorted(
                        response['Datapoints'], key=lambda x: x['Timestamp'])
                    print(
                        f"✓ Collected {len(metrics[key])} datapoints for {key}")

                except Exception as e:
                    print(f"✗ Error collecting {config['name']}: {e}")

        return metrics

    def get_task_count(self, service_name, cluster_name, start_time, end_time, period=60):
        """
        Get ECS task count over time (DesiredTaskCount and RunningTaskCount)
        """
        task_metrics = {}

        for metric_name in ['DesiredTaskCount', 'RunningTaskCount']:
            try:
                response = self.cloudwatch.get_metric_statistics(
                    Namespace='ECS/ContainerInsights',
                    MetricName=metric_name,
                    Dimensions=[
                        {'Name': 'ServiceName', 'Value': service_name},
                        {'Name': 'ClusterName', 'Value': cluster_name}
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=period,
                    Statistics=['Average']
                )

                task_metrics[metric_name] = sorted(
                    response['Datapoints'], key=lambda x: x['Timestamp'])
                print(
                    f"✓ Collected {len(task_metrics[metric_name])} datapoints for {metric_name}")

            except Exception as e:
                print(f"✗ Error collecting {metric_name}: {e}")

        return task_metrics

    def get_alb_metrics(self, load_balancer_name, start_time, end_time, period=60):
        """
        Collect ALB metrics for request count and response time
        """
        metrics = {}

        # Extract ALB ARN suffix from full name
        lb_suffix = load_balancer_name.split(
            '/')[-1] if '/' in load_balancer_name else load_balancer_name

        metric_configs = [
            {
                'name': 'RequestCount',
                'stat': ['Sum'],
                'unit': 'Count'
            },
            {
                'name': 'TargetResponseTime',
                'stat': ['Average'],
                'unit': 'Seconds'
            },
            {
                'name': 'HealthyHostCount',
                'stat': ['Average'],
                'unit': 'Count'
            },
            {
                'name': 'UnHealthyHostCount',
                'stat': ['Average'],
                'unit': 'Count'
            }
        ]

        for config in metric_configs:
            for stat in config['stat']:
                try:
                    response = self.cloudwatch.get_metric_statistics(
                        Namespace='AWS/ApplicationELB',
                        MetricName=config['name'],
                        Dimensions=[
                            {'Name': 'LoadBalancer', 'Value': lb_suffix}
                        ],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=period,
                        Statistics=[stat]
                    )

                    key = f"ALB_{config['name']}_{stat}"
                    metrics[key] = sorted(
                        response['Datapoints'], key=lambda x: x['Timestamp'])
                    print(
                        f"✓ Collected {len(metrics[key])} datapoints for {key}")

                except Exception as e:
                    print(f"✗ Error collecting ALB {config['name']}: {e}")

        return metrics

    def detect_autoscaling_events(self, task_count_data):
        """
        Detect when autoscaling occurred by finding task count changes
        """
        events = []

        if 'DesiredTaskCount' not in task_count_data or len(task_count_data['DesiredTaskCount']) < 2:
            return events

        datapoints = task_count_data['DesiredTaskCount']

        for i in range(1, len(datapoints)):
            prev_count = datapoints[i-1]['Average']
            curr_count = datapoints[i]['Average']

            if curr_count != prev_count:
                events.append({
                    'timestamp': datapoints[i]['Timestamp'],
                    'from_count': int(prev_count),
                    'to_count': int(curr_count),
                    'change': int(curr_count - prev_count)
                })

        return events

    def save_metrics_to_csv(self, metrics, output_file):
        """
        Save all metrics to CSV for further analysis
        """
        # Combine all metrics into a single dataframe
        all_data = []

        for metric_name, datapoints in metrics.items():
            for dp in datapoints:
                stat_key = [k for k in dp.keys() if k not in [
                    'Timestamp', 'Unit']][0]
                all_data.append({
                    'Timestamp': dp['Timestamp'],
                    'Metric': metric_name,
                    'Value': dp[stat_key],
                    'Unit': dp.get('Unit', 'None')
                })

        df = pd.DataFrame(all_data)
        df = df.sort_values('Timestamp')
        df.to_csv(output_file, index=False)
        print(f"\n✓ Saved metrics to {output_file}")

        return df

    def plot_metrics(self, metrics, task_metrics, autoscaling_events, strategy_name, output_file):
        """
        Generate comprehensive visualization of all metrics
        """
        fig, axes = plt.subplots(4, 1, figsize=(14, 12))
        fig.suptitle(
            f'Infrastructure Metrics - {strategy_name} Strategy', fontsize=16, fontweight='bold')

        # Plot 1: Task Count with autoscaling events
        ax1 = axes[0]
        if 'DesiredTaskCount' in task_metrics:
            desired_data = task_metrics['DesiredTaskCount']
            timestamps = [dp['Timestamp'] for dp in desired_data]
            values = [dp['Average'] for dp in desired_data]
            ax1.plot(timestamps, values, 'b-o', linewidth=2,
                     markersize=4, label='Desired Tasks')

        if 'RunningTaskCount' in task_metrics:
            running_data = task_metrics['RunningTaskCount']
            timestamps = [dp['Timestamp'] for dp in running_data]
            values = [dp['Average'] for dp in running_data]
            ax1.plot(timestamps, values, 'g--s', linewidth=2,
                     markersize=4, label='Running Tasks')

        # Mark autoscaling events
        for event in autoscaling_events:
            ax1.axvline(x=event['timestamp'], color='red',
                        linestyle=':', alpha=0.7)
            ax1.text(event['timestamp'], ax1.get_ylim()[1] * 0.95,
                     f"+{event['change']}" if event['change'] > 0 else str(
                         event['change']),
                     rotation=90, va='top', fontsize=8, color='red')

        ax1.set_ylabel('Task Count', fontsize=11, fontweight='bold')
        ax1.set_title('ECS Task Count & Autoscaling Events', fontsize=12)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)

        # Plot 2: CPU Utilization
        ax2 = axes[1]
        if 'CPUUtilization_Average' in metrics:
            cpu_data = metrics['CPUUtilization_Average']
            timestamps = [dp['Timestamp'] for dp in cpu_data]
            values = [dp['Average'] for dp in cpu_data]
            ax2.plot(timestamps, values, 'r-o', linewidth=2,
                     markersize=3, label='CPU Average')

        if 'CPUUtilization_Maximum' in metrics:
            cpu_max_data = metrics['CPUUtilization_Maximum']
            timestamps = [dp['Timestamp'] for dp in cpu_max_data]
            values = [dp['Maximum'] for dp in cpu_max_data]
            ax2.plot(timestamps, values, 'darkred',
                     linewidth=1, alpha=0.5, label='CPU Max')

        ax2.axhline(y=80, color='orange', linestyle='--',
                    linewidth=1.5, label='Threshold (80%)')
        ax2.set_ylabel('CPU Utilization (%)', fontsize=11, fontweight='bold')
        ax2.set_title('CPU Utilization', fontsize=12)
        ax2.legend(loc='upper left')
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(0, 100)

        # Plot 3: Memory Utilization
        ax3 = axes[2]
        if 'MemoryUtilization_Average' in metrics:
            mem_data = metrics['MemoryUtilization_Average']
            timestamps = [dp['Timestamp'] for dp in mem_data]
            values = [dp['Average'] for dp in mem_data]
            ax3.plot(timestamps, values, 'purple', linewidth=2,
                     markersize=3, label='Memory Average')

        if 'MemoryUtilization_Maximum' in metrics:
            mem_max_data = metrics['MemoryUtilization_Maximum']
            timestamps = [dp['Timestamp'] for dp in mem_max_data]
            values = [dp['Maximum'] for dp in mem_max_data]
            ax3.plot(timestamps, values, 'darkviolet',
                     linewidth=1, alpha=0.5, label='Memory Max')

        ax3.axhline(y=80, color='orange', linestyle='--',
                    linewidth=1.5, label='Threshold (80%)')
        ax3.set_ylabel('Memory Utilization (%)',
                       fontsize=11, fontweight='bold')
        ax3.set_title('Memory Utilization', fontsize=12)
        ax3.legend(loc='upper left')
        ax3.grid(True, alpha=0.3)
        ax3.set_ylim(0, 100)

        # Plot 4: ALB Healthy Host Count
        ax4 = axes[3]
        if 'ALB_HealthyHostCount_Average' in metrics:
            healthy_data = metrics['ALB_HealthyHostCount_Average']
            timestamps = [dp['Timestamp'] for dp in healthy_data]
            values = [dp['Average'] for dp in healthy_data]
            ax4.plot(timestamps, values, 'g-o', linewidth=2,
                     markersize=3, label='Healthy Hosts')

        if 'ALB_UnHealthyHostCount_Average' in metrics:
            unhealthy_data = metrics['ALB_UnHealthyHostCount_Average']
            timestamps = [dp['Timestamp'] for dp in unhealthy_data]
            values = [dp['Average'] for dp in unhealthy_data]
            ax4.plot(timestamps, values, 'r-x', linewidth=2,
                     markersize=5, label='Unhealthy Hosts')

        ax4.set_ylabel('Host Count', fontsize=11, fontweight='bold')
        ax4.set_xlabel('Time', fontsize=11, fontweight='bold')
        ax4.set_title('ALB Target Health Status', fontsize=12)
        ax4.legend(loc='upper left')
        ax4.grid(True, alpha=0.3)

        # Format x-axis for all subplots
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=5))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ Saved plot to {output_file}")
        plt.close()


def main():
    parser = argparse.ArgumentParser(
        description='Collect CloudWatch metrics for autoscaling analysis')
    parser.add_argument('--strategy', required=True, choices=['push', 'pull', 'hybrid'],
                        help='Fanout strategy being tested')
    parser.add_argument('--service-name', default='timeline-service',
                        help='ECS service name')
    parser.add_argument('--cluster-name', default='timeline-service',
                        help='ECS cluster name')
    parser.add_argument('--alb-name', default='app/cs6650-project-dev-alb/951608096.us-west-2',
                        help='ALB name (format: app/name/id)')
    parser.add_argument('--duration', type=int, default=30,
                        help='Duration to collect metrics (minutes from now backwards)')
    parser.add_argument('--region', default='us-west-2',
                        help='AWS region')
    parser.add_argument('--output-dir', default='./results',
                        help='Output directory for results')

    args = parser.parse_args()

    # Setup time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=args.duration)

    print(f"\n{'='*70}")
    print(f"CloudWatch Metrics Collection - {args.strategy.upper()} Strategy")
    print(f"{'='*70}")
    print(f"Service: {args.service_name}")
    print(f"Cluster: {args.cluster_name}")
    print(
        f"Time Range: {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {args.duration} minutes")
    print(f"{'='*70}\n")

    # Initialize collector
    collector = CloudWatchMetricsCollector(region=args.region)

    # Collect ECS metrics
    print("📊 Collecting ECS Service Metrics...")
    ecs_metrics = collector.get_ecs_metrics(
        args.service_name,
        args.cluster_name,
        start_time,
        end_time,
        period=60
    )

    # Collect task count metrics
    print("\n📊 Collecting Task Count Metrics...")
    task_metrics = collector.get_task_count(
        args.service_name,
        args.cluster_name,
        start_time,
        end_time,
        period=60
    )

    # Collect ALB metrics
    print("\n📊 Collecting ALB Metrics...")
    alb_metrics = collector.get_alb_metrics(
        args.alb_name,
        start_time,
        end_time,
        period=60
    )

    # Combine all metrics
    all_metrics = {**ecs_metrics, **alb_metrics}

    # Detect autoscaling events
    print("\n🔍 Detecting Autoscaling Events...")
    autoscaling_events = collector.detect_autoscaling_events(task_metrics)

    if autoscaling_events:
        print(f"\n✓ Found {len(autoscaling_events)} autoscaling events:")
        for event in autoscaling_events:
            change_str = f"+{event['change']}" if event['change'] > 0 else str(
                event['change'])
            print(
                f"  • {event['timestamp'].strftime('%H:%M:%S')} - Tasks: {event['from_count']} → {event['to_count']} ({change_str})")
    else:
        print("  ℹ No autoscaling events detected")

    # Save to CSV
    import os
    os.makedirs(args.output_dir, exist_ok=True)

    csv_file = f"{args.output_dir}/metrics_{args.strategy}.csv"
    collector.save_metrics_to_csv(all_metrics, csv_file)

    # Save autoscaling events
    if autoscaling_events:
        events_file = f"{args.output_dir}/autoscaling_events_{args.strategy}.json"
        with open(events_file, 'w') as f:
            json.dump([{
                'timestamp': e['timestamp'].isoformat(),
                'from_count': e['from_count'],
                'to_count': e['to_count'],
                'change': e['change']
            } for e in autoscaling_events], f, indent=2)
        print(f"✓ Saved autoscaling events to {events_file}")

    # Generate plot
    print("\n📈 Generating visualization...")
    plot_file = f"{args.output_dir}/infrastructure_{args.strategy}.png"
    collector.plot_metrics(all_metrics, task_metrics,
                           autoscaling_events, args.strategy.upper(), plot_file)

    print(f"\n{'='*70}")
    print("✓ Metrics collection completed successfully!")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
