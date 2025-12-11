"""
Performance Analysis and Visualization for Fanout Strategy Comparison
Analyzes Locust test results and ECS autoscaling metrics
Generates comprehensive comparison charts
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np
from datetime import datetime

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10

# Results directory
RESULTS_DIR = Path("results")
OUTPUT_DIR = RESULTS_DIR / "analysis"
OUTPUT_DIR.mkdir(exist_ok=True)

# Strategy names
STRATEGIES = ["push", "pull", "hybrid"]
STRATEGY_COLORS = {
    "push": "#2ecc71",    # Green
    "pull": "#3498db",    # Blue
    "hybrid": "#e74c3c"   # Red
}

def load_locust_data(strategy):
    """Load Locust test data history for a strategy"""
    possible_files = [
        RESULTS_DIR / f"locust_data_{strategy}_stats_history.csv",
        RESULTS_DIR / f"locust_data_{strategy}_512mb_4tasks_stats_history.csv",
        RESULTS_DIR / f"{strategy}_1024mb_20251209_023819_stats_history.csv",
        RESULTS_DIR / f"{strategy}_1024mb_20251209_011144_stats_history.csv",
        RESULTS_DIR / f"{strategy}_1024mb_20251209_150854_stats_history.csv"
    ]
    
    stats_file = None
    for f in possible_files:
        if f.exists():
            stats_file = f
            break
    
    if stats_file is None:
        print(f"Warning: No stats history file found for {strategy}")
        return None
    
    print(f"Loading: {stats_file.name}")
    df = pd.read_csv(stats_file)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='s')
    df['Strategy'] = strategy.upper()
    return df

def load_locust_stats(strategy):
    """Load Locust summary stats for a strategy"""
    possible_files = [
        RESULTS_DIR / f"locust_data_{strategy}_stats.csv",
        RESULTS_DIR / f"locust_data_{strategy}_512mb_4tasks_stats.csv",
        RESULTS_DIR / f"{strategy}_1024mb_20251209_023819_stats.csv",
        RESULTS_DIR / f"{strategy}_1024mb_20251209_011144_stats.csv",
        RESULTS_DIR / f"{strategy}_1024mb_20251209_150854_stats.csv"
    ]
    
    stats_file = None
    for f in possible_files:
        if f.exists():
            stats_file = f
            break
    
    if stats_file is None:
        print(f"Warning: No stats file found for {strategy}")
        return None
    
    df = pd.read_csv(stats_file)
    df['Strategy'] = strategy.upper()
    return df

def load_service_monitor_data(filename):
    """Load ECS service monitoring data"""
    monitor_file = RESULTS_DIR / filename
    
    if not monitor_file.exists():
        print(f"Warning: {monitor_file} not found")
        return None
    
    df = pd.read_csv(monitor_file)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    return df

def plot_individual_strategy_performance(strategy, monitor_filename=None):
    """Generate individual charts for each strategy showing RPS, throughput and autoscaling"""
    df_history = load_locust_data(strategy)
    df_stats = load_locust_stats(strategy)
    
    if df_history is None:
        print(f"Skipping {strategy} - no data found")
        return
    
    # Filter for Aggregated data only (stats_history only has aggregated)
    df_agg = df_history[df_history['Name'] == 'Aggregated'].copy()
    
    # Create 2x2 subplot layout
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
    
    # Calculate elapsed time in minutes
    if len(df_agg) > 0:
        df_agg['Minutes'] = (df_agg['Timestamp'] - df_agg['Timestamp'].min()).dt.total_seconds() / 60
    
    # Get endpoint-specific stats from stats.csv
    read_rps = 0
    write_rps = 0
    read_p50 = 0
    read_p95 = 0
    write_p50 = 0
    write_p95 = 0
    
    if df_stats is not None:
        read_row = df_stats[df_stats['Name'] == 'GET /api/timeline/:user_id']
        write_row = df_stats[df_stats['Name'] == 'POST /api/posts']
        
        if len(read_row) > 0:
            read_rps = read_row['Requests/s'].values[0]
            read_p50 = read_row['50%'].values[0]
            read_p95 = read_row['95%'].values[0]
        
        if len(write_row) > 0:
            write_rps = write_row['Requests/s'].values[0]
            write_p50 = write_row['50%'].values[0]
            write_p95 = write_row['95%'].values[0]
    
    # 1. Overall RPS over time
    ax1 = fig.add_subplot(gs[0, 0])
    if len(df_agg) > 0:
        ax1.plot(df_agg['Minutes'], df_agg['Requests/s'], 
                color=STRATEGY_COLORS[strategy], linewidth=2, alpha=0.8)
        ax1.fill_between(df_agg['Minutes'], df_agg['Requests/s'], alpha=0.3, color=STRATEGY_COLORS[strategy])
    ax1.set_title(f'Total Requests/Second Over Time - {strategy.upper()}', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Time (minutes)', fontsize=10)
    ax1.set_ylabel('Total Requests/Second', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 2. Read vs Write RPS (Bar Chart from stats)
    ax2 = fig.add_subplot(gs[0, 1])
    operations = ['Read\n(GET timeline)', 'Write\n(POST)']
    rps_values = [read_rps, write_rps]
    bars = ax2.bar(operations, rps_values, color=[STRATEGY_COLORS[strategy], STRATEGY_COLORS[strategy]], 
                   alpha=0.7, edgecolor='black', linewidth=1.5)
    ax2.set_title(f'Average RPS by Operation - {strategy.upper()}', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Requests/Second', fontsize=10)
    ax2.grid(True, alpha=0.3, axis='y')
    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}',
                ha='center', va='bottom', fontweight='bold', fontsize=9)
    
    # 3. Response Time over time (p50 and p95)
    ax3 = fig.add_subplot(gs[1, 0])
    if len(df_agg) > 0:
        ax3.plot(df_agg['Minutes'], df_agg['50%'], 
                label='p50 (Median)', color=STRATEGY_COLORS[strategy], linewidth=2, alpha=0.8)
        ax3.plot(df_agg['Minutes'], df_agg['95%'], 
                label='p95', color=STRATEGY_COLORS[strategy], linewidth=2, linestyle='--', alpha=0.8)
    ax3.set_title(f'Response Time Over Time - {strategy.upper()}', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Time (minutes)', fontsize=10)
    ax3.set_ylabel('Response Time (ms)', fontsize=10)
    ax3.legend(loc='best')
    ax3.grid(True, alpha=0.3)
    
    # 4. Response Time Comparison (Bar Chart)
    ax4 = fig.add_subplot(gs[1, 1])
    x = np.arange(2)
    width = 0.35
    
    ax4.bar(x - width/2, [read_p50, write_p50], width, label='p50 (Median)', 
           color=STRATEGY_COLORS[strategy], alpha=0.7, edgecolor='black')
    ax4.bar(x + width/2, [read_p95, write_p95], width, label='p95', 
           color=STRATEGY_COLORS[strategy], alpha=0.4, edgecolor='black')
    
    ax4.set_title(f'Response Time by Operation - {strategy.upper()}', fontsize=12, fontweight='bold')
    ax4.set_ylabel('Response Time (ms)', fontsize=10)
    ax4.set_xticks(x)
    ax4.set_xticklabels(['Read\n(GET timeline)', 'Write\n(POST)'])
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')
    
    # 5. Autoscaling behavior (spans both columns)
    ax5 = fig.add_subplot(gs[2, :])
    if monitor_filename:
        monitor_df = load_service_monitor_data(monitor_filename)
        if monitor_df is not None:
            services = ['timeline-service', 'post-service', 'user-service', 'social-graph-service', 'web-service']
            service_colors = {
                'timeline-service': '#e74c3c',
                'post-service': '#3498db',
                'user-service': '#2ecc71',
                'social-graph-service': '#f39c12',
                'web-service': '#9b59b6'
            }
            
            # Group by timestamp to get iterations
            unique_timestamps = monitor_df['Timestamp'].unique()
            timestamp_to_iteration = {ts: idx for idx, ts in enumerate(unique_timestamps)}
            monitor_df['Iteration'] = monitor_df['Timestamp'].map(timestamp_to_iteration)
            
            for service in services:
                service_data = monitor_df[monitor_df['Service'] == service]
                if len(service_data) > 0:
                    # Plot running tasks (solid line)
                    ax5.plot(service_data['Iteration'], service_data['RunningTasks'], 
                           label=f'{service} (Running)', color=service_colors[service], 
                           linewidth=2.5, marker='o', markersize=4, alpha=0.8)
                    # Plot desired tasks (dashed line)
                    ax5.plot(service_data['Iteration'], service_data['DesiredTasks'], 
                           color=service_colors[service], 
                           linewidth=1.5, linestyle='--', alpha=0.5)
            
            ax5.set_title(f'ECS Container Autoscaling - {strategy.upper()} (Solid=Running, Dashed=Desired)', 
                         fontsize=12, fontweight='bold')
            ax5.set_xlabel('Iteration (30s interval)', fontsize=10)
            ax5.set_ylabel('Task Count', fontsize=10)
            ax5.legend(loc='best', fontsize=8, ncol=3)
            ax5.grid(True, alpha=0.3)
            ax5.set_ylim(bottom=0)
    
    fig.suptitle(f'{strategy.upper()} Strategy Performance Analysis', fontsize=16, fontweight='bold', y=0.995)
    
    plt.savefig(OUTPUT_DIR / f'{strategy}_complete_analysis.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {OUTPUT_DIR / f'{strategy}_complete_analysis.png'}")
    plt.close()

def plot_rps_comparison():
    """Plot RPS (Requests Per Second) comparison across strategies"""
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    for strategy in STRATEGIES:
        df = load_locust_data(strategy)
        if df is None:
            continue
        
        # Use aggregated data from stats_history
        df_agg = df[df['Name'] == 'Aggregated'].copy()
        
        # Calculate elapsed time in minutes
        if len(df_agg) > 0:
            df_agg['Minutes'] = (df_agg['Timestamp'] - df_agg['Timestamp'].min()).dt.total_seconds() / 60
            
            # Plot total RPS over time
            axes[0].plot(df_agg['Minutes'], df_agg['Requests/s'], 
                        label=strategy.upper(), color=STRATEGY_COLORS[strategy], 
                        linewidth=2, alpha=0.8)
    
    # Get average RPS by operation from stats.csv for bar chart
    read_rps_values = []
    write_rps_values = []
    strategy_labels = []
    
    for strategy in STRATEGIES:
        df_stats = load_locust_stats(strategy)
        if df_stats is None:
            continue
        
        strategy_labels.append(strategy.upper())
        
        read_row = df_stats[df_stats['Name'] == 'GET /api/timeline/:user_id']
        write_row = df_stats[df_stats['Name'] == 'POST /api/posts']
        
        read_rps_values.append(read_row['Requests/s'].values[0] if len(read_row) > 0 else 0)
        write_rps_values.append(write_row['Requests/s'].values[0] if len(write_row) > 0 else 0)
    
    # Configure RPS over time subplot
    axes[0].set_title('Total Requests Per Second Over Time', 
                     fontsize=14, fontweight='bold')
    axes[0].set_xlabel('Time (minutes)', fontsize=12)
    axes[0].set_ylabel('Requests/Second', fontsize=12)
    axes[0].legend(loc='best', fontsize=11)
    axes[0].grid(True, alpha=0.3)
    
    # Configure average RPS by operation (bar chart)
    x = np.arange(len(strategy_labels))
    width = 0.35
    
    bars1 = axes[1].bar(x - width/2, read_rps_values, width, label='Read (GET timeline)', 
                        color=[STRATEGY_COLORS[s.lower()] for s in strategy_labels], alpha=0.7, edgecolor='black')
    bars2 = axes[1].bar(x + width/2, write_rps_values, width, label='Write (POST)', 
                        color=[STRATEGY_COLORS[s.lower()] for s in strategy_labels], alpha=0.4, edgecolor='black')
    
    axes[1].set_title('Average RPS by Operation', fontsize=14, fontweight='bold')
    axes[1].set_ylabel('Requests/Second', fontsize=12)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(strategy_labels)
    axes[1].legend(loc='best', fontsize=11)
    axes[1].grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar in bars1:
        height = bar.get_height()
        axes[1].text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}', ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        height = bar.get_height()
        axes[1].text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'rps_comparison.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {OUTPUT_DIR / 'rps_comparison.png'}")
    plt.close()

def plot_response_time_comparison():
    """Plot response time comparison across strategies"""
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    
    # Collect data from stats.csv for bar charts
    strategy_labels = []
    read_p50_values = []
    read_p95_values = []
    write_p50_values = []
    write_p95_values = []
    
    for strategy in STRATEGIES:
        df_stats = load_locust_stats(strategy)
        if df_stats is None:
            continue
        
        strategy_labels.append(strategy.upper())
        
        read_row = df_stats[df_stats['Name'] == 'GET /api/timeline/:user_id']
        write_row = df_stats[df_stats['Name'] == 'POST /api/posts']
        
        if len(read_row) > 0:
            read_p50_values.append(read_row['50%'].values[0])
            read_p95_values.append(read_row['95%'].values[0])
        else:
            read_p50_values.append(0)
            read_p95_values.append(0)
        
        if len(write_row) > 0:
            write_p50_values.append(write_row['50%'].values[0])
            write_p95_values.append(write_row['95%'].values[0])
        else:
            write_p50_values.append(0)
            write_p95_values.append(0)
    
    x = np.arange(len(strategy_labels))
    width = 0.6
    colors = [STRATEGY_COLORS[s.lower()] for s in strategy_labels]
    
    # Read p50
    bars1 = axes[0, 0].bar(x, read_p50_values, width, color=colors, alpha=0.7, edgecolor='black')
    axes[0, 0].set_title('Read Operations - Median Response Time (p50)', fontsize=12, fontweight='bold')
    axes[0, 0].set_ylabel('Response Time (ms)', fontsize=11)
    axes[0, 0].set_xticks(x)
    axes[0, 0].set_xticklabels(strategy_labels)
    axes[0, 0].grid(True, alpha=0.3, axis='y')
    for bar in bars1:
        height = bar.get_height()
        axes[0, 0].text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.0f}', ha='center', va='bottom', fontsize=9)
    
    # Read p95
    bars2 = axes[0, 1].bar(x, read_p95_values, width, color=colors, alpha=0.7, edgecolor='black')
    axes[0, 1].set_title('Read Operations - 95th Percentile (p95)', fontsize=12, fontweight='bold')
    axes[0, 1].set_ylabel('Response Time (ms)', fontsize=11)
    axes[0, 1].set_xticks(x)
    axes[0, 1].set_xticklabels(strategy_labels)
    axes[0, 1].grid(True, alpha=0.3, axis='y')
    for bar in bars2:
        height = bar.get_height()
        axes[0, 1].text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.0f}', ha='center', va='bottom', fontsize=9)
    
    # Write p50
    bars3 = axes[1, 0].bar(x, write_p50_values, width, color=colors, alpha=0.7, edgecolor='black')
    axes[1, 0].set_title('Write Operations - Median Response Time (p50)', fontsize=12, fontweight='bold')
    axes[1, 0].set_ylabel('Response Time (ms)', fontsize=11)
    axes[1, 0].set_xticks(x)
    axes[1, 0].set_xticklabels(strategy_labels)
    axes[1, 0].grid(True, alpha=0.3, axis='y')
    for bar in bars3:
        height = bar.get_height()
        axes[1, 0].text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.0f}', ha='center', va='bottom', fontsize=9)
    
    # Write p95
    bars4 = axes[1, 1].bar(x, write_p95_values, width, color=colors, alpha=0.7, edgecolor='black')
    axes[1, 1].set_title('Write Operations - 95th Percentile (p95)', fontsize=12, fontweight='bold')
    axes[1, 1].set_ylabel('Response Time (ms)', fontsize=11)
    axes[1, 1].set_xticks(x)
    axes[1, 1].set_xticklabels(strategy_labels)
    axes[1, 1].grid(True, alpha=0.3, axis='y')
    for bar in bars4:
        height = bar.get_height()
        axes[1, 1].text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.0f}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'response_time_comparison.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {OUTPUT_DIR / 'response_time_comparison.png'}")
    plt.close()

def plot_failure_rate_comparison():
    """Plot failure rate comparison across strategies"""
    fig, ax = plt.subplots(figsize=(14, 6))
    
    for strategy in STRATEGIES:
        df = load_locust_data(strategy)
        if df is None:
            continue
        
        # Calculate failure rate
        aggregated = df[df['Name'] == 'Aggregated'].copy()
        if len(aggregated) > 0:
            aggregated['Minutes'] = (aggregated['Timestamp'] - aggregated['Timestamp'].min()).dt.total_seconds() / 60
            aggregated['Failure_Rate'] = (aggregated['Total Failure Count'] / 
                                         (aggregated['Total Request Count'] + 0.001)) * 100  # Avoid division by zero
            
            ax.plot(aggregated['Minutes'], aggregated['Failure_Rate'], 
                   label=strategy.upper(), color=STRATEGY_COLORS[strategy], 
                   linewidth=2, alpha=0.8)
    
    ax.set_title('Failure Rate Comparison Across Strategies', fontsize=14, fontweight='bold')
    ax.set_xlabel('Time (minutes)', fontsize=12)
    ax.set_ylabel('Failure Rate (%)', fontsize=12)
    ax.legend(loc='best', fontsize=11)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'failure_rate_comparison.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {OUTPUT_DIR / 'failure_rate_comparison.png'}")
    plt.close()

def plot_autoscaling_behavior(monitor_files):
    """Plot ECS autoscaling behavior for each test"""
    services = ['timeline-service', 'post-service', 'user-service', 'social-graph-service', 'web-service']
    service_colors = {
        'timeline-service': '#e74c3c',
        'post-service': '#3498db',
        'user-service': '#2ecc71',
        'social-graph-service': '#f39c12',
        'web-service': '#9b59b6'
    }
    
    fig, axes = plt.subplots(len(monitor_files), 1, figsize=(14, 6 * len(monitor_files)))
    
    if len(monitor_files) == 1:
        axes = [axes]
    
    for idx, (test_name, filename) in enumerate(monitor_files.items()):
        df = load_service_monitor_data(filename)
        if df is None:
            continue
        
        ax = axes[idx]
        
        # Group by timestamp to get iterations
        unique_timestamps = df['Timestamp'].unique()
        timestamp_to_iteration = {ts: idx for idx, ts in enumerate(unique_timestamps)}
        df['Iteration'] = df['Timestamp'].map(timestamp_to_iteration)
        
        # Plot running and desired tasks for each service
        for service in services:
            service_data = df[df['Service'] == service]
            if len(service_data) > 0:
                # Running tasks (solid line with markers)
                ax.plot(service_data['Iteration'], service_data['RunningTasks'], 
                       label=f'{service} (Running)', color=service_colors[service], 
                       linewidth=2.5, marker='o', markersize=4, alpha=0.8)
                # Desired tasks (dashed line)
                ax.plot(service_data['Iteration'], service_data['DesiredTasks'], 
                       color=service_colors[service], 
                       linewidth=1.5, linestyle='--', alpha=0.5)
        
        ax.set_title(f'ECS Container Autoscaling - {test_name} (Solid=Running, Dashed=Desired)', 
                    fontsize=14, fontweight='bold')
        ax.set_xlabel('Iteration (30s interval)', fontsize=12)
        ax.set_ylabel('Task Count', fontsize=12)
        ax.legend(loc='best', fontsize=9, ncol=3)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(bottom=0)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'autoscaling_behavior.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {OUTPUT_DIR / 'autoscaling_behavior.png'}")
    plt.close()

def generate_summary_statistics():
    """Generate summary statistics table"""
    summary_data = []
    
    for strategy in STRATEGIES:
        df_stats = load_locust_stats(strategy)
        if df_stats is None:
            continue
        
        # Get read operations stats
        read_stats = df_stats[df_stats['Name'] == 'GET /api/timeline/:user_id']
        # Get write operations stats
        write_stats = df_stats[df_stats['Name'] == 'POST /api/posts']
        # Get aggregated stats
        agg_stats = df_stats[df_stats['Name'] == 'Aggregated']
        
        if len(read_stats) > 0:
            summary_data.append({
                'Strategy': strategy.upper(),
                'Operation': 'READ',
                'Total Requests': read_stats['Request Count'].values[0],
                'Failure Count': read_stats['Failure Count'].values[0],
                'Median RT (ms)': read_stats['Median Response Time'].values[0],
                'P95 RT (ms)': read_stats['95%'].values[0],
                'P99 RT (ms)': read_stats['99%'].values[0],
                'Avg RPS': read_stats['Requests/s'].values[0],
                'Failure Rate (%)': (read_stats['Failure Count'].values[0] / 
                                    max(read_stats['Request Count'].values[0], 1)) * 100
            })
        
        if len(write_stats) > 0:
            summary_data.append({
                'Strategy': strategy.upper(),
                'Operation': 'WRITE',
                'Total Requests': write_stats['Request Count'].values[0],
                'Failure Count': write_stats['Failure Count'].values[0],
                'Median RT (ms)': write_stats['Median Response Time'].values[0],
                'P95 RT (ms)': write_stats['95%'].values[0],
                'P99 RT (ms)': write_stats['99%'].values[0],
                'Avg RPS': write_stats['Requests/s'].values[0],
                'Failure Rate (%)': (write_stats['Failure Count'].values[0] / 
                                    max(write_stats['Request Count'].values[0], 1)) * 100
            })
    
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(OUTPUT_DIR / 'summary_statistics.csv', index=False)
    print(f"✓ Saved: {OUTPUT_DIR / 'summary_statistics.csv'}")
    
    # Create a formatted table visualization
    fig, ax = plt.subplots(figsize=(16, 8))
    ax.axis('tight')
    ax.axis('off')
    
    # Check if we have data to display
    if len(summary_df) == 0:
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center', fontsize=20)
        plt.savefig(OUTPUT_DIR / "summary_table.png", dpi=300, bbox_inches='tight')
        print("✓ Saved: results\\analysis\\summary_table.png (no data)")
        plt.close()
        return summary_df
    
    # Format numeric columns only
    display_df = summary_df.copy()
    numeric_cols = ['Total Requests', 'Failure Count', 'Median RT (ms)', 'P95 RT (ms)', 
                    'P99 RT (ms)', 'Avg RPS', 'Failure Rate (%)']
    for col in numeric_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].round(2)
    
    table = ax.table(cellText=display_df.values, 
                    colLabels=display_df.columns,
                    cellLoc='center',
                    loc='center',
                    colWidths=[0.08, 0.08, 0.12, 0.1, 0.12, 0.1, 0.1, 0.1, 0.12])
    
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)
    
    # Color header
    for i in range(len(display_df.columns)):
        table[(0, i)].set_facecolor('#34495e')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Color strategy rows
    for i, row in enumerate(display_df.itertuples(), start=1):
        strategy = row.Strategy.lower()
        color = STRATEGY_COLORS.get(strategy, '#ecf0f1')
        table[(i, 0)].set_facecolor(color)
        table[(i, 0)].set_text_props(weight='bold', color='white')
    
    plt.title('Performance Summary Statistics', fontsize=16, fontweight='bold', pad=20)
    plt.savefig(OUTPUT_DIR / 'summary_table.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {OUTPUT_DIR / 'summary_table.png'}")
    plt.close()
    
    return summary_df

def plot_throughput_bar_comparison():
    """Create bar chart comparing average throughput"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    read_throughput = []
    write_throughput = []
    strategies = []
    
    for strategy in STRATEGIES:
        df_stats = load_locust_stats(strategy)
        if df_stats is None:
            continue
        
        read_stats = df_stats[df_stats['Name'] == 'GET /api/timeline/:user_id']
        write_stats = df_stats[df_stats['Name'] == 'POST /api/posts']
        
        if len(read_stats) > 0:
            read_throughput.append(read_stats['Requests/s'].values[0])
        else:
            read_throughput.append(0)
        
        if len(write_stats) > 0:
            write_throughput.append(write_stats['Requests/s'].values[0])
        else:
            write_throughput.append(0)
        
        strategies.append(strategy.upper())
    
    # Plot read throughput
    bars1 = axes[0].bar(strategies, read_throughput, 
                       color=[STRATEGY_COLORS[s.lower()] for s in strategies],
                       alpha=0.8, edgecolor='black', linewidth=1.5)
    axes[0].set_title('Average Read Throughput (RPS)', fontsize=14, fontweight='bold')
    axes[0].set_ylabel('Requests/Second', fontsize=12)
    axes[0].grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar in bars1:
        height = bar.get_height()
        axes[0].text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}',
                    ha='center', va='bottom', fontweight='bold')
    
    # Plot write throughput
    bars2 = axes[1].bar(strategies, write_throughput, 
                       color=[STRATEGY_COLORS[s.lower()] for s in strategies],
                       alpha=0.8, edgecolor='black', linewidth=1.5)
    axes[1].set_title('Average Write Throughput (RPS)', fontsize=14, fontweight='bold')
    axes[1].set_ylabel('Requests/Second', fontsize=12)
    axes[1].grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar in bars2:
        height = bar.get_height()
        axes[1].text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}',
                    ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'throughput_bar_comparison.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {OUTPUT_DIR / 'throughput_bar_comparison.png'}")
    plt.close()

def main():
    """Main analysis function"""
    print("\n" + "="*60)
    print("Fanout Strategy Performance Analysis")
    print("="*60 + "\n")
    
    # Map strategies to monitor files
    strategy_monitors = {
        'push': 'service_monitor_2025-12-09_150913.csv',
        'pull': 'service_monitor_2025-12-09_023815.csv',
        'hybrid': 'service_monitor_2025-12-09_011150.csv'
    }
    
    # Generate individual strategy charts
    print("="*60)
    print("Generating individual strategy performance charts...")
    print("="*60)
    for strategy in STRATEGIES:
        print(f"\n📊 Analyzing {strategy.upper()} strategy...")
        monitor_file = strategy_monitors.get(strategy)
        plot_individual_strategy_performance(strategy, monitor_file)
    
    # Generate comparison charts
    print("\n" + "="*60)
    print("Generating comparison charts...")
    print("="*60)
    
    print("\nGenerating RPS comparison charts...")
    plot_rps_comparison()
    
    print("Generating response time comparison charts...")
    plot_response_time_comparison()
    
    print("Generating failure rate comparison...")
    plot_failure_rate_comparison()
    
    print("Generating throughput bar comparison...")
    plot_throughput_bar_comparison()
    
    print("Generating autoscaling behavior charts...")
    monitor_files = {
        'PUSH Strategy': 'service_monitor_2025-12-09_150913.csv',
        'PULL Strategy': 'service_monitor_2025-12-09_023815.csv',
        'HYBRID Strategy': 'service_monitor_2025-12-09_011150.csv'
    }
    plot_autoscaling_behavior(monitor_files)
    
    print("\nGenerating summary statistics...")
    summary_df = generate_summary_statistics()
    
    print("\n" + "="*60)
    print("Analysis Complete!")
    print(f"All charts saved to: {OUTPUT_DIR}")
    print("="*60)
    
    print("\n📊 Summary Statistics Preview:")
    print(summary_df.to_string(index=False))
    print()

if __name__ == "__main__":
    main()
