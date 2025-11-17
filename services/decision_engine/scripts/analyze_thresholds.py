"""
Analyze optimal threshold distribution across 10 seeds.
"""

import json
import numpy as np
from pathlib import Path

SEEDS = [42, 123, 456, 789, 1024, 2048, 3141, 5926, 2718, 2024]

def main():
    models_dir = Path(__file__).parent.parent / "models"
    
    thresholds = []
    optimal_metrics = []
    
    print("="*80)
    print("Optimal Threshold Analysis")
    print("="*80)
    print("\nIndividual Results:")
    print("-"*80)
    
    for seed in SEEDS:
        metrics_path = models_dir / f"model_metrics_v2_seed_{seed}.json"
        with open(metrics_path, 'r') as f:
            data = json.load(f)
        
        threshold = data['metrics_optimal_threshold']['threshold']
        optimal_acc = data['metrics_optimal_threshold']['accuracy']
        optimal_prec = data['metrics_optimal_threshold']['precision']
        optimal_rec = data['metrics_optimal_threshold']['recall']
        optimal_f1 = data['metrics_optimal_threshold']['f1']
        
        thresholds.append(threshold)
        optimal_metrics.append({
            'accuracy': optimal_acc,
            'precision': optimal_prec,
            'recall': optimal_rec,
            'f1': optimal_f1
        })
        
        print(f"Seed {seed:4d}: Threshold={threshold:.4f}, F1={optimal_f1:.4f}, Acc={optimal_acc:.4f}, Prec={optimal_prec:.4f}, Rec={optimal_rec:.4f}")
    
    # Calculate statistics
    thresholds = np.array(thresholds)
    
    print("\n" + "="*80)
    print("Threshold Statistics")
    print("="*80)
    print(f"Mean:   {np.mean(thresholds):.4f}")
    print(f"Std:    {np.std(thresholds, ddof=1):.4f}")
    print(f"Min:    {np.min(thresholds):.4f}")
    print(f"Max:    {np.max(thresholds):.4f}")
    print(f"Range:  {np.max(thresholds) - np.min(thresholds):.4f}")
    print(f"CV:     {np.std(thresholds, ddof=1) / np.mean(thresholds) * 100:.2f}%")
    
    # Optimal metrics statistics
    print("\n" + "="*80)
    print("Optimal Metrics Statistics (at best F1 threshold)")
    print("="*80)
    
    for metric_name in ['accuracy', 'precision', 'recall', 'f1']:
        values = [m[metric_name] for m in optimal_metrics]
        print(f"\n{metric_name.capitalize()}:")
        print(f"  Mean:  {np.mean(values):.4f}")
        print(f"  Std:   {np.std(values, ddof=1):.4f}")
        print(f"  Range: [{np.min(values):.4f}, {np.max(values):.4f}]")
    
    # Analysis
    print("\n" + "="*80)
    print("Critical Analysis")
    print("="*80)
    
    threshold_range = np.max(thresholds) - np.min(thresholds)
    threshold_cv = np.std(thresholds, ddof=1) / np.mean(thresholds) * 100
    
    print(f"\n1. Threshold Stability:")
    if threshold_cv < 10:
        print(f"   [OK] CV={threshold_cv:.2f}% < 10%, thresholds are relatively stable")
    elif threshold_cv < 20:
        print(f"   [WARN] CV={threshold_cv:.2f}% in [10%, 20%), moderate instability")
    else:
        print(f"   [FAIL] CV={threshold_cv:.2f}% >= 20%, severe instability")
    
    print(f"\n2. Threshold Range Impact:")
    print(f"   Range: {threshold_range:.4f} ({threshold_range/np.mean(thresholds)*100:.1f}% of mean)")
    if threshold_range > 0.15:
        print(f"   [CRITICAL] Range > 0.15, different seeds produce drastically different decision boundaries")
    elif threshold_range > 0.10:
        print(f"   [WARN] Range > 0.10, significant variation in decision boundaries")
    else:
        print(f"   [OK] Range <= 0.10, acceptable variation")
    
    print(f"\n3. Practical Implications:")
    print(f"   - If using fixed threshold=0.5:")
    print(f"     * All models use same threshold, but suboptimal for each")
    print(f"   - If using optimal threshold per model:")
    print(f"     * Threshold varies from {np.min(thresholds):.4f} to {np.max(thresholds):.4f}")
    print(f"     * In production, which threshold to use? (model selection problem)")
    print(f"   - Recommendation:")
    if threshold_cv < 10:
        print(f"     * Use mean threshold {np.mean(thresholds):.4f} as production threshold")
    else:
        print(f"     * Threshold instability suggests model is unreliable for production")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()

