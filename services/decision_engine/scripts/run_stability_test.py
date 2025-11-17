"""
Stability Test Runner for v2.6-multifreq-full

This script runs the training script 10 times with different random seeds
to validate model stability and reproducibility.

Seeds: 42, 123, 456, 789, 1024, 2048, 3141, 5926, 2718, 2024
"""

import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime

# Define random seeds for stability testing
SEEDS = [42, 123, 456, 789, 1024, 2048, 3141, 5926, 2718, 2024]

def run_training(seed: int) -> dict:
    """
    Run training script with specified seed.
    
    Args:
        seed: Random seed
        
    Returns:
        Dictionary containing metrics or error info
    """
    print(f"\n{'='*80}")
    print(f"Running training with seed={seed} ({SEEDS.index(seed)+1}/{len(SEEDS)})")
    print(f"{'='*80}\n")
    
    try:
        # Run training script
        result = subprocess.run(
            [sys.executable, "services/decision_engine/scripts/train_xgboost_v2_6.py", "--seed", str(seed)],
            cwd=Path(__file__).parent.parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )
        
        # Check if training succeeded
        if result.returncode not in [0, 1]:  # 0=excellent, 1=insufficient but completed
            print(f"[ERROR] Training failed with return code {result.returncode}")
            print(f"STDERR: {result.stderr}")
            return {
                'seed': seed,
                'success': False,
                'error': f"Return code {result.returncode}",
                'stderr': result.stderr
            }
        
        # Read metrics file
        metrics_path = Path(__file__).parent.parent / "models" / f"model_metrics_v2_seed_{seed}.json"
        
        if not metrics_path.exists():
            print(f"[ERROR] Metrics file not found: {metrics_path}")
            return {
                'seed': seed,
                'success': False,
                'error': "Metrics file not found"
            }
        
        with open(metrics_path, 'r') as f:
            metrics_data = json.load(f)
        
        # Extract key metrics
        metrics = metrics_data['metrics']
        training_info = metrics_data['training_info']
        
        result_summary = {
            'seed': seed,
            'success': True,
            'auc': metrics['auc'],
            'pr_auc': metrics['pr_auc'],
            'accuracy': metrics['accuracy'],
            'precision': metrics['precision'],
            'recall': metrics['recall'],
            'f1': metrics['f1'],
            'pred_bullish_ratio': metrics_data['prediction_distribution']['predicted_bullish_ratio'],
            'valid_samples': training_info['valid_samples'],
            'train_size': training_info['train_size'],
            'val_size': training_info['val_size']
        }
        
        print(f"\n[SUCCESS] Seed {seed} completed:")
        print(f"  AUC: {result_summary['auc']:.4f}")
        print(f"  PR-AUC: {result_summary['pr_auc']:.4f}")
        print(f"  Accuracy: {result_summary['accuracy']:.4f}")
        print(f"  F1: {result_summary['f1']:.4f}")
        
        return result_summary
        
    except subprocess.TimeoutExpired:
        print(f"[ERROR] Training timed out after 10 minutes")
        return {
            'seed': seed,
            'success': False,
            'error': "Timeout after 10 minutes"
        }
    except Exception as e:
        print(f"[ERROR] Unexpected error: {str(e)}")
        return {
            'seed': seed,
            'success': False,
            'error': str(e)
        }


def main():
    """Run stability test with all seeds."""
    print("="*80)
    print("v2.6-multifreq-full Stability Test")
    print("="*80)
    print(f"Seeds: {SEEDS}")
    print(f"Total runs: {len(SEEDS)}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    results = []
    failed_seeds = []
    
    for seed in SEEDS:
        result = run_training(seed)
        results.append(result)
        
        if not result['success']:
            failed_seeds.append(seed)
    
    # Save aggregated results
    output_path = Path(__file__).parent.parent / "models" / "stability_results.json"
    with open(output_path, 'w') as f:
        json.dump({
            'seeds': SEEDS,
            'total_runs': len(SEEDS),
            'successful_runs': len([r for r in results if r['success']]),
            'failed_runs': len(failed_seeds),
            'failed_seeds': failed_seeds,
            'results': results,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"\n{'='*80}")
    print("Stability Test Complete")
    print(f"{'='*80}")
    print(f"Total runs: {len(SEEDS)}")
    print(f"Successful: {len([r for r in results if r['success']])}")
    print(f"Failed: {len(failed_seeds)}")
    if failed_seeds:
        print(f"Failed seeds: {failed_seeds}")
    print(f"Results saved to: {output_path}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()

