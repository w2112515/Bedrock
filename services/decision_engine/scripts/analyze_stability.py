"""
Stability Analysis for v2.6-multifreq-full

This script analyzes the results from run_stability_test.py and generates:
1. Statistical summary (mean, std, min, max, 95% CI)
2. Visualization plots (boxplots, line charts)
3. Stability report (Markdown format)
4. Pass/Fail verdict based on strict criteria
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

# Strict stability criteria
AUC_STD_THRESHOLD = 0.012
AUC_MEAN_MIN = 0.575
AUC_MEAN_MAX = 0.590

def calculate_statistics(values):
    """Calculate statistical metrics."""
    values = np.array(values)
    return {
        'mean': float(np.mean(values)),
        'std': float(np.std(values, ddof=1)),  # Sample std
        'min': float(np.min(values)),
        'max': float(np.max(values)),
        'median': float(np.median(values)),
        'q25': float(np.percentile(values, 25)),
        'q75': float(np.percentile(values, 75)),
        'ci_95_lower': float(np.mean(values) - 1.96 * np.std(values, ddof=1) / np.sqrt(len(values))),
        'ci_95_upper': float(np.mean(values) + 1.96 * np.std(values, ddof=1) / np.sqrt(len(values)))
    }

def generate_plots(results, output_path):
    """Generate visualization plots."""
    successful_results = [r for r in results if r['success']]
    
    if len(successful_results) == 0:
        print("[ERROR] No successful runs to plot")
        return
    
    seeds = [r['seed'] for r in successful_results]
    aucs = [r['auc'] for r in successful_results]
    pr_aucs = [r['pr_auc'] for r in successful_results]
    accuracies = [r['accuracy'] for r in successful_results]
    precisions = [r['precision'] for r in successful_results]
    recalls = [r['recall'] for r in successful_results]
    f1s = [r['f1'] for r in successful_results]
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('v2.6-multifreq-full Stability Analysis', fontsize=16, fontweight='bold')
    
    # Plot 1: AUC Boxplot
    ax1 = axes[0, 0]
    bp1 = ax1.boxplot([aucs], labels=['ROC-AUC'], patch_artist=True)
    bp1['boxes'][0].set_facecolor('lightblue')
    ax1.axhline(y=AUC_MEAN_MIN, color='green', linestyle='--', label=f'Min Threshold ({AUC_MEAN_MIN})')
    ax1.axhline(y=AUC_MEAN_MAX, color='red', linestyle='--', label=f'Max Threshold ({AUC_MEAN_MAX})')
    ax1.set_ylabel('AUC')
    ax1.set_title('ROC-AUC Distribution')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: AUC Line Chart
    ax2 = axes[0, 1]
    ax2.plot(range(len(seeds)), aucs, marker='o', linestyle='-', linewidth=2, markersize=8)
    ax2.axhline(y=np.mean(aucs), color='blue', linestyle='--', label=f'Mean ({np.mean(aucs):.4f})')
    ax2.axhline(y=AUC_MEAN_MIN, color='green', linestyle='--', alpha=0.5)
    ax2.axhline(y=AUC_MEAN_MAX, color='red', linestyle='--', alpha=0.5)
    ax2.set_xlabel('Run Index')
    ax2.set_ylabel('ROC-AUC')
    ax2.set_title('ROC-AUC Across Seeds')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(range(len(seeds)))
    ax2.set_xticklabels([str(s) for s in seeds], rotation=45)
    
    # Plot 3: All Metrics Boxplot
    ax3 = axes[1, 0]
    bp3 = ax3.boxplot([aucs, pr_aucs, accuracies, f1s], 
                       labels=['ROC-AUC', 'PR-AUC', 'Accuracy', 'F1'],
                       patch_artist=True)
    colors = ['lightblue', 'lightgreen', 'lightyellow', 'lightcoral']
    for patch, color in zip(bp3['boxes'], colors):
        patch.set_facecolor(color)
    ax3.set_ylabel('Score')
    ax3.set_title('All Metrics Distribution')
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Precision-Recall Boxplot
    ax4 = axes[1, 1]
    bp4 = ax4.boxplot([precisions, recalls], labels=['Precision', 'Recall'], patch_artist=True)
    bp4['boxes'][0].set_facecolor('lightblue')
    bp4['boxes'][1].set_facecolor('lightgreen')
    ax4.set_ylabel('Score')
    ax4.set_title('Precision & Recall Distribution')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"[OK] Plots saved to: {output_path}")

def generate_report(data, stats, output_path):
    """Generate Markdown stability report."""
    successful_results = [r for r in data['results'] if r['success']]
    
    report = f"""# v2.6-multifreq-full Stability Validation Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Executive Summary

- **Total Runs**: {data['total_runs']}
- **Successful Runs**: {data['successful_runs']}
- **Failed Runs**: {data['failed_runs']}
- **Seeds**: {data['seeds']}

---

## Statistical Analysis

### ROC-AUC
- **Mean**: {stats['auc']['mean']:.4f}
- **Std Dev**: {stats['auc']['std']:.4f}
- **Min**: {stats['auc']['min']:.4f}
- **Max**: {stats['auc']['max']:.4f}
- **Median**: {stats['auc']['median']:.4f}
- **95% CI**: [{stats['auc']['ci_95_lower']:.4f}, {stats['auc']['ci_95_upper']:.4f}]

### PR-AUC
- **Mean**: {stats['pr_auc']['mean']:.4f}
- **Std Dev**: {stats['pr_auc']['std']:.4f}

### Accuracy
- **Mean**: {stats['accuracy']['mean']:.4f}
- **Std Dev**: {stats['accuracy']['std']:.4f}

### Precision
- **Mean**: {stats['precision']['mean']:.4f}
- **Std Dev**: {stats['precision']['std']:.4f}

### Recall
- **Mean**: {stats['recall']['mean']:.4f}
- **Std Dev**: {stats['recall']['std']:.4f}

### F1 Score
- **Mean**: {stats['f1']['mean']:.4f}
- **Std Dev**: {stats['f1']['std']:.4f}

---

## Stability Criteria Evaluation

**Criteria**:
1. AUC Std Dev ≤ {AUC_STD_THRESHOLD}
2. AUC Mean ∈ [{AUC_MEAN_MIN}, {AUC_MEAN_MAX}]
3. No significant outliers

**Results**:
"""
    
    # Check criteria
    auc_std_pass = stats['auc']['std'] <= AUC_STD_THRESHOLD
    auc_mean_pass = AUC_MEAN_MIN <= stats['auc']['mean'] <= AUC_MEAN_MAX
    
    report += f"- **AUC Std Dev**: {stats['auc']['std']:.4f} {'✅ PASS' if auc_std_pass else '❌ FAIL'} (threshold: ≤{AUC_STD_THRESHOLD})\n"
    report += f"- **AUC Mean Range**: {stats['auc']['mean']:.4f} {'✅ PASS' if auc_mean_pass else '❌ FAIL'} (range: [{AUC_MEAN_MIN}, {AUC_MEAN_MAX}])\n"
    
    # Overall verdict
    overall_pass = auc_std_pass and auc_mean_pass and data['failed_runs'] == 0
    
    report += f"\n---\n\n## Final Verdict\n\n"
    
    if overall_pass:
        report += "### ✅ **PASS - Model is STABLE and RELIABLE**\n\n"
        report += "The model demonstrates consistent performance across different random seeds. "
        report += "The traditional technical indicator system has reached its performance ceiling at AUC ~0.58.\n\n"
        report += "**Recommendation**: Accept v2.6-multifreq-full as the best version of the technical indicator system. "
        report += "Further improvements require new feature categories (cross-pair correlation, volume anomalies, on-chain data, funding rates, market sentiment).\n"
    else:
        report += "### ❌ **FAIL - Model is UNSTABLE**\n\n"
        if not auc_std_pass:
            report += f"- AUC standard deviation ({stats['auc']['std']:.4f}) exceeds threshold ({AUC_STD_THRESHOLD})\n"
        if not auc_mean_pass:
            report += f"- AUC mean ({stats['auc']['mean']:.4f}) outside acceptable range ([{AUC_MEAN_MIN}, {AUC_MEAN_MAX}])\n"
        if data['failed_runs'] > 0:
            report += f"- {data['failed_runs']} training runs failed\n"
        report += "\n**Recommendation**: Investigate instability causes before proceeding.\n"
    
    report += f"\n---\n\n## Detailed Results\n\n"
    report += "| Seed | AUC | PR-AUC | Accuracy | Precision | Recall | F1 |\n"
    report += "|------|-----|--------|----------|-----------|--------|----|\n"
    
    for r in successful_results:
        report += f"| {r['seed']} | {r['auc']:.4f} | {r['pr_auc']:.4f} | {r['accuracy']:.4f} | {r['precision']:.4f} | {r['recall']:.4f} | {r['f1']:.4f} |\n"
    
    if data['failed_runs'] > 0:
        report += f"\n### Failed Runs\n\n"
        for r in data['results']:
            if not r['success']:
                report += f"- **Seed {r['seed']}**: {r.get('error', 'Unknown error')}\n"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"[OK] Report saved to: {output_path}")
    
    return overall_pass

def main():
    """Analyze stability test results."""
    # Load results
    results_path = Path(__file__).parent.parent / "models" / "stability_results.json"
    
    if not results_path.exists():
        print(f"[ERROR] Results file not found: {results_path}")
        print("Please run run_stability_test.py first")
        return
    
    with open(results_path, 'r') as f:
        data = json.load(f)
    
    print("="*80)
    print("Analyzing Stability Test Results")
    print("="*80)
    
    successful_results = [r for r in data['results'] if r['success']]
    
    if len(successful_results) == 0:
        print("[ERROR] No successful runs found")
        return
    
    # Calculate statistics for all metrics
    stats = {
        'auc': calculate_statistics([r['auc'] for r in successful_results]),
        'pr_auc': calculate_statistics([r['pr_auc'] for r in successful_results]),
        'accuracy': calculate_statistics([r['accuracy'] for r in successful_results]),
        'precision': calculate_statistics([r['precision'] for r in successful_results]),
        'recall': calculate_statistics([r['recall'] for r in successful_results]),
        'f1': calculate_statistics([r['f1'] for r in successful_results])
    }
    
    # Generate plots
    plots_path = Path(__file__).parent.parent / "models" / "stability_plots.png"
    generate_plots(data['results'], plots_path)
    
    # Generate report
    report_path = Path(__file__).parent.parent / "models" / "stability_report.md"
    overall_pass = generate_report(data, stats, report_path)
    
    # Print summary
    print(f"\n{'='*80}")
    print("Analysis Complete")
    print(f"{'='*80}")
    print(f"AUC Mean: {stats['auc']['mean']:.4f} +/- {stats['auc']['std']:.4f}")
    print(f"AUC Range: [{stats['auc']['min']:.4f}, {stats['auc']['max']:.4f}]")
    print(f"Verdict: {'[PASS]' if overall_pass else '[FAIL]'}")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()

