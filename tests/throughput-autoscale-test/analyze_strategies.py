"""
Fanout Strategy Comparison Analysis
Compares PUSH, PULL, and HYBRID strategies for the social media platform
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (15, 10)
plt.rcParams['font.size'] = 10

# Load stats data for all three strategies
results_dir = Path('results')

# PUSH strategy
push_stats = pd.read_csv(results_dir / 'push_1024mb_20251209_150854_stats.csv')
push_history = pd.read_csv(results_dir / 'push_1024mb_20251209_150854_stats_history.csv')

# PULL strategy
pull_stats = pd.read_csv(results_dir / 'pull_1024mb_20251209_023819_stats.csv')
pull_history = pd.read_csv(results_dir / 'pull_1024mb_20251209_023819_stats_history.csv')

# HYBRID strategy
hybrid_stats = pd.read_csv(results_dir / 'hybrid_1024mb_20251209_011144_stats.csv')
hybrid_history = pd.read_csv(results_dir / 'hybrid_1024mb_20251209_011144_stats_history.csv')

# Create figure with multiple subplots
fig = plt.figure(figsize=(20, 14))

# ========== 1. Overall Performance Comparison ==========
ax1 = plt.subplot(3, 3, 1)
strategies = ['PUSH', 'PULL', 'HYBRID']
total_requests = [
    push_stats[push_stats['Name'] == 'Aggregated']['Request Count'].values[0],
    pull_stats[pull_stats['Name'] == 'Aggregated']['Request Count'].values[0],
    hybrid_stats[hybrid_stats['Name'] == 'Aggregated']['Request Count'].values[0]
]
total_failures = [
    push_stats[push_stats['Name'] == 'Aggregated']['Failure Count'].values[0],
    pull_stats[pull_stats['Name'] == 'Aggregated']['Failure Count'].values[0],
    hybrid_stats[hybrid_stats['Name'] == 'Aggregated']['Failure Count'].values[0]
]

x = np.arange(len(strategies))
width = 0.35
bars1 = ax1.bar(x - width/2, total_requests, width, label='Total Requests', color='#2ecc71')
bars2 = ax1.bar(x + width/2, total_failures, width, label='Failures', color='#e74c3c')

ax1.set_ylabel('Count')
ax1.set_title('Total Requests vs Failures')
ax1.set_xticks(x)
ax1.set_xticklabels(strategies)
ax1.legend()
ax1.grid(True, alpha=0.3)

# Add value labels on bars
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height):,}',
                ha='center', va='bottom', fontsize=8)

# ========== 2. Request Throughput (RPS) ==========
ax2 = plt.subplot(3, 3, 2)
rps_values = [
    push_stats[push_stats['Name'] == 'Aggregated']['Requests/s'].values[0],
    pull_stats[pull_stats['Name'] == 'Aggregated']['Requests/s'].values[0],
    hybrid_stats[hybrid_stats['Name'] == 'Aggregated']['Requests/s'].values[0]
]
bars = ax2.bar(strategies, rps_values, color=['#3498db', '#e67e22', '#9b59b6'])
ax2.set_ylabel('Requests/Second')
ax2.set_title('Average Throughput (RPS)')
ax2.grid(True, alpha=0.3)

for i, (bar, val) in enumerate(zip(bars, rps_values)):
    ax2.text(bar.get_x() + bar.get_width()/2., val,
            f'{val:.1f}',
            ha='center', va='bottom', fontweight='bold')

# ========== 3. Failure Rate Comparison ==========
ax3 = plt.subplot(3, 3, 3)
failure_rates = [
    (total_failures[i] / total_requests[i] * 100) if total_requests[i] > 0 else 0
    for i in range(3)
]
colors = ['#2ecc71' if rate < 1 else '#f39c12' if rate < 10 else '#e74c3c' for rate in failure_rates]
bars = ax3.bar(strategies, failure_rates, color=colors)
ax3.set_ylabel('Failure Rate (%)')
ax3.set_title('Request Failure Rate')
ax3.axhline(y=1, color='orange', linestyle='--', alpha=0.5, label='1% threshold')
ax3.axhline(y=10, color='red', linestyle='--', alpha=0.5, label='10% threshold')
ax3.legend()
ax3.grid(True, alpha=0.3)

for bar, val in zip(bars, failure_rates):
    ax3.text(bar.get_x() + bar.get_width()/2., val,
            f'{val:.2f}%',
            ha='center', va='bottom', fontweight='bold')

# ========== 4. Response Time Comparison ==========
ax4 = plt.subplot(3, 3, 4)
response_times = {
    'Median': [
        push_stats[push_stats['Name'] == 'Aggregated']['Median Response Time'].values[0],
        pull_stats[pull_stats['Name'] == 'Aggregated']['Median Response Time'].values[0],
        hybrid_stats[hybrid_stats['Name'] == 'Aggregated']['Median Response Time'].values[0]
    ],
    'Average': [
        push_stats[push_stats['Name'] == 'Aggregated']['Average Response Time'].values[0],
        pull_stats[pull_stats['Name'] == 'Aggregated']['Average Response Time'].values[0],
        hybrid_stats[hybrid_stats['Name'] == 'Aggregated']['Average Response Time'].values[0]
    ],
    'P95': [
        push_stats[push_stats['Name'] == 'Aggregated']['95%'].values[0],
        pull_stats[pull_stats['Name'] == 'Aggregated']['95%'].values[0],
        hybrid_stats[hybrid_stats['Name'] == 'Aggregated']['95%'].values[0]
    ],
    'P99': [
        push_stats[push_stats['Name'] == 'Aggregated']['99%'].values[0],
        pull_stats[pull_stats['Name'] == 'Aggregated']['99%'].values[0],
        hybrid_stats[hybrid_stats['Name'] == 'Aggregated']['99%'].values[0]
    ]
}

x = np.arange(len(strategies))
width = 0.2
for i, (metric, values) in enumerate(response_times.items()):
    ax4.bar(x + i*width - 1.5*width, values, width, label=metric)

ax4.set_ylabel('Response Time (ms)')
ax4.set_title('Response Time Distribution')
ax4.set_xticks(x)
ax4.set_xticklabels(strategies)
ax4.legend()
ax4.grid(True, alpha=0.3)

# ========== 5. Throughput Over Time ==========
ax5 = plt.subplot(3, 3, 5)
# Normalize timestamps to relative seconds
push_history['relative_time'] = (push_history['Timestamp'] - push_history['Timestamp'].min())
pull_history['relative_time'] = (pull_history['Timestamp'] - pull_history['Timestamp'].min())
hybrid_history['relative_time'] = (hybrid_history['Timestamp'] - hybrid_history['Timestamp'].min())

ax5.plot(push_history['relative_time'], push_history['Requests/s'], 
         label='PUSH', color='#3498db', linewidth=2, alpha=0.8)
ax5.plot(pull_history['relative_time'], pull_history['Requests/s'], 
         label='PULL', color='#e67e22', linewidth=2, alpha=0.8)
ax5.plot(hybrid_history['relative_time'], hybrid_history['Requests/s'], 
         label='HYBRID', color='#9b59b6', linewidth=2, alpha=0.8)

ax5.set_xlabel('Time (seconds)')
ax5.set_ylabel('Requests/Second')
ax5.set_title('Throughput Over Time')
ax5.legend()
ax5.grid(True, alpha=0.3)

# ========== 6. Response Time Over Time ==========
ax6 = plt.subplot(3, 3, 6)
ax6.plot(push_history['relative_time'], push_history['Total Median Response Time'], 
         label='PUSH', color='#3498db', linewidth=2, alpha=0.8)
ax6.plot(pull_history['relative_time'], pull_history['Total Median Response Time'], 
         label='PULL', color='#e67e22', linewidth=2, alpha=0.8)
ax6.plot(hybrid_history['relative_time'], hybrid_history['Total Median Response Time'], 
         label='HYBRID', color='#9b59b6', linewidth=2, alpha=0.8)

ax6.set_xlabel('Time (seconds)')
ax6.set_ylabel('Median Response Time (ms)')
ax6.set_title('Response Time Over Time')
ax6.legend()
ax6.grid(True, alpha=0.3)

# ========== 7. User Load Over Time ==========
ax7 = plt.subplot(3, 3, 7)
ax7.plot(push_history['relative_time'], push_history['User Count'], 
         label='PUSH', color='#3498db', linewidth=2, alpha=0.8)
ax7.plot(pull_history['relative_time'], pull_history['User Count'], 
         label='PULL', color='#e67e22', linewidth=2, alpha=0.8)
ax7.plot(hybrid_history['relative_time'], hybrid_history['User Count'], 
         label='HYBRID', color='#9b59b6', linewidth=2, alpha=0.8)

ax7.set_xlabel('Time (seconds)')
ax7.set_ylabel('Concurrent Users')
ax7.set_title('User Load Ramp-up')
ax7.legend()
ax7.grid(True, alpha=0.3)

# ========== 8. Read vs Write Performance ==========
ax8 = plt.subplot(3, 3, 8)
strategies_ops = []
read_times = []
write_times = []

for name, stats in [('PUSH', push_stats), ('PULL', pull_stats), ('HYBRID', hybrid_stats)]:
    read_row = stats[stats['Name'] == 'GET /api/timeline/:user_id']
    write_row = stats[stats['Name'] == 'POST /api/posts']
    
    if not read_row.empty and not write_row.empty:
        strategies_ops.append(name)
        read_times.append(read_row['Median Response Time'].values[0])
        write_times.append(write_row['Median Response Time'].values[0])

x = np.arange(len(strategies_ops))
width = 0.35
bars1 = ax8.bar(x - width/2, read_times, width, label='READ (Timeline)', color='#3498db')
bars2 = ax8.bar(x + width/2, write_times, width, label='WRITE (Post)', color='#e74c3c')

ax8.set_ylabel('Median Response Time (ms)')
ax8.set_title('Read vs Write Performance')
ax8.set_xticks(x)
ax8.set_xticklabels(strategies_ops)
ax8.legend()
ax8.grid(True, alpha=0.3)

# Add value labels
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax8.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}ms',
                ha='center', va='bottom', fontsize=8)

# ========== 9. Summary Table ==========
ax9 = plt.subplot(3, 3, 9)
ax9.axis('off')

summary_data = []
for name, stats in [('PUSH', push_stats), ('PULL', pull_stats), ('HYBRID', hybrid_stats)]:
    agg = stats[stats['Name'] == 'Aggregated']
    summary_data.append([
        name,
        f"{agg['Request Count'].values[0]:,}",
        f"{agg['Failure Count'].values[0]:,}",
        f"{agg['Requests/s'].values[0]:.1f}",
        f"{agg['Median Response Time'].values[0]:.0f}",
        f"{agg['95%'].values[0]:.0f}",
        f"{agg['99%'].values[0]:.0f}"
    ])

table = ax9.table(cellText=summary_data,
                  colLabels=['Strategy', 'Requests', 'Failures', 'RPS', 'Median(ms)', 'P95(ms)', 'P99(ms)'],
                  cellLoc='center',
                  loc='center',
                  colWidths=[0.12, 0.15, 0.12, 0.12, 0.13, 0.13, 0.13])

table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1, 2)

# Color code the rows
for i in range(1, 4):
    for j in range(7):
        cell = table[(i, j)]
        if i == 1:  # PUSH
            cell.set_facecolor('#d6eaf8')
        elif i == 2:  # PULL
            cell.set_facecolor('#fdebd0')
        else:  # HYBRID
            cell.set_facecolor('#e8daef')

ax9.set_title('Performance Summary', fontweight='bold', pad=20)

plt.tight_layout()
plt.savefig(results_dir / 'analysis' / 'strategy_comparison.png', dpi=300, bbox_inches='tight')
print(f"✓ Chart saved: {results_dir / 'analysis' / 'strategy_comparison.png'}")

# ========== Generate Analysis Report ==========
print("\n" + "="*80)
print("FANOUT STRATEGY COMPARISON ANALYSIS")
print("="*80)

for name, stats in [('PUSH', push_stats), ('PULL', pull_stats), ('HYBRID', hybrid_stats)]:
    agg = stats[stats['Name'] == 'Aggregated']
    read_row = stats[stats['Name'] == 'GET /api/timeline/:user_id']
    write_row = stats[stats['Name'] == 'POST /api/posts']
    
    print(f"\n{name} Strategy:")
    print(f"  Total Requests: {agg['Request Count'].values[0]:,}")
    print(f"  Total Failures: {agg['Failure Count'].values[0]:,}")
    print(f"  Failure Rate: {(agg['Failure Count'].values[0] / agg['Request Count'].values[0] * 100):.2f}%")
    print(f"  Throughput: {agg['Requests/s'].values[0]:.2f} req/s")
    print(f"  Response Time - Median: {agg['Median Response Time'].values[0]:.0f}ms")
    print(f"  Response Time - P95: {agg['95%'].values[0]:.0f}ms")
    print(f"  Response Time - P99: {agg['99%'].values[0]:.0f}ms")
    
    if not read_row.empty:
        print(f"  READ (Timeline) - Median: {read_row['Median Response Time'].values[0]:.0f}ms")
        print(f"  READ (Timeline) - Failure Rate: {(read_row['Failure Count'].values[0] / read_row['Request Count'].values[0] * 100):.2f}%")
    
    if not write_row.empty:
        print(f"  WRITE (Post) - Median: {write_row['Median Response Time'].values[0]:.0f}ms")
        print(f"  WRITE (Post) - Failure Rate: {(write_row['Failure Count'].values[0] / write_row['Request Count'].values[0] * 100):.2f}%")

print("\n" + "="*80)
print("KEY FINDINGS:")
print("="*80)

# Calculate winners
max_rps_idx = np.argmax([
    push_stats[push_stats['Name'] == 'Aggregated']['Requests/s'].values[0],
    pull_stats[pull_stats['Name'] == 'Aggregated']['Requests/s'].values[0],
    hybrid_stats[hybrid_stats['Name'] == 'Aggregated']['Requests/s'].values[0]
])

min_response_idx = np.argmin([
    push_stats[push_stats['Name'] == 'Aggregated']['Median Response Time'].values[0],
    pull_stats[pull_stats['Name'] == 'Aggregated']['Median Response Time'].values[0],
    hybrid_stats[hybrid_stats['Name'] == 'Aggregated']['Median Response Time'].values[0]
])

min_failure_idx = np.argmin(failure_rates)

print(f"\n🏆 Best Throughput: {strategies[max_rps_idx]}")
print(f"🏆 Best Response Time: {strategies[min_response_idx]}")
print(f"🏆 Lowest Failure Rate: {strategies[min_failure_idx]}")

print("\n" + "="*80)
print("ARCHITECTURAL INSIGHTS:")
print("="*80)

print("""
1. PUSH Strategy (SNS Fan-out):
   - Writes happen asynchronously via SNS
   - Timeline reads are fast (pre-computed)
   - Best for write-heavy workloads with many followers
   - Trade-off: Higher write latency, storage overhead

2. PULL Strategy (On-demand):
   - Writes are fast (just store the post)
   - Timeline reads query multiple sources (slower)
   - Best for read-light workloads or users with few followers
   - Trade-off: High read latency, potential hotspots

3. HYBRID Strategy (Adaptive):
   - Uses PUSH for users with < 50k followers
   - Uses PULL for celebrity users (>= 50k followers)
   - Balances write and read performance
   - Trade-off: Implementation complexity, threshold tuning
""")

plt.show()
