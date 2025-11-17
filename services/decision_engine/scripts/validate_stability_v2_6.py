"""
Stability Validation Script for XGBoost Model v2.6 - Multi-Frequency Features (REFACTORED).

This script implements a two-phase stability validation methodology:

Phase 1: Hyperparameter Optimization (Optional)
- Run training with seed=42 and HPO enabled
- Extract and save the best hyperparameters

Phase 2: Fixed-Hyperparameter Stability Validation
- Train with 10 different random seeds using FIXED hyperparameters
- Only vary random_state, keep all other factors constant
- Calculate stability statistics (mean, std, CV, 95% CI)
- Assess stability using graded criteria

Usage:
    # Phase 1 + Phase 2 (full pipeline)
    python services/decision_engine/scripts/validate_stability_v2_6.py

    # Phase 2 only (use existing hyperparameters)
    python services/decision_engine/scripts/validate_stability_v2_6.py --skip-hpo
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import subprocess
import json
import numpy as np
import argparse
from pathlib import Path
from datetime import datetime
import structlog
from scipy import stats as scipy_stats

# Setup logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer()
    ]
)
logger = structlog.get_logger()

# Random seeds for stability validation
SEEDS = [42, 123, 456, 789, 1024, 2048, 3141, 5926, 2718, 2024]

# Stability assessment criteria (adjusted based on user decision)
STABILITY_CRITERIA = {
    'EXCELLENT': {'std': 0.005, 'cv': 1.0, 'ci_width': 0.02},
    'GOOD': {'std': 0.008, 'cv': 1.5, 'ci_width': 0.03},
    'ACCEPTABLE': {'std': 0.01, 'cv': 2.0, 'ci_width': 0.04},
    'POOR': {'std': float('inf'), 'cv': float('inf'), 'ci_width': float('inf')}
}

def run_hpo_phase(version: str = "v2_7", seed: int = 42) -> str:
    """
    Phase 1: Run hyperparameter optimization with seed=42.

    Args:
        version: Model version (v2_6 or v2_7)
        seed: Random seed for HPO

    Returns:
        Path to saved hyperparameters JSON file
    """
    logger.info("=" * 80)
    logger.info(f"Phase 1: Hyperparameter Optimization ({version})")
    logger.info("=" * 80)
    logger.info(f"Running HPO with seed={seed}...")
    logger.info("")

    script_name = f"train_xgboost_{version}.py"
    result = subprocess.run(
        ["python", f"services/decision_engine/scripts/{script_name}", "--seed", str(seed)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        logger.error(f"HPO failed: {result.stderr}")
        raise RuntimeError(f"HPO failed for {version} seed={seed}")

    # Load metrics and extract best hyperparameters
    model_dir = Path(__file__).parent.parent / "models"
    metrics_path = model_dir / f"model_metrics_{version}_seed_{seed}.json"

    with open(metrics_path, 'r') as f:
        data = json.load(f)

    best_params = data['training_info']['best_hyperparameters']

    if not best_params:
        raise RuntimeError(f"No hyperparameters found in metrics file")

    # Save best hyperparameters
    hyperparams_path = model_dir / f"best_hyperparameters_{version}.json"
    with open(hyperparams_path, 'w') as f:
        json.dump(best_params, f, indent=2)

    logger.info(f"[OK] HPO complete: AUC={data['metrics']['auc']:.4f}")
    logger.info(f"Best hyperparameters saved: {hyperparams_path}")
    logger.info("")

    return str(hyperparams_path)


def run_training_with_fixed_hyperparameters(version: str, seed: int, hyperparams_path: str) -> dict:
    """
    Run training with fixed hyperparameters.

    Args:
        version: Model version (v2_6 or v2_7)
        seed: Random seed
        hyperparams_path: Path to fixed hyperparameters JSON

    Returns:
        Metrics dictionary
    """
    logger.info(f"Training {version} with seed={seed} (fixed hyperparameters)...")

    script_name = f"train_xgboost_{version}.py"
    result = subprocess.run(
        ["python", f"services/decision_engine/scripts/{script_name}",
         "--seed", str(seed),
         "--fixed-hyperparameters", hyperparams_path],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        logger.error(f"Training failed for seed={seed}: {result.stderr}")
        return None

    # Load metrics
    model_dir = Path(__file__).parent.parent / "models"
    metrics_path = model_dir / f"model_metrics_{version}_seed_{seed}.json"

    with open(metrics_path, 'r') as f:
        full_metrics = json.load(f)

    # Extract relevant metrics
    metrics = {
        'auc': full_metrics['metrics']['auc'],
        'pr_auc': full_metrics['metrics']['pr_auc'],
        'accuracy': full_metrics['metrics']['accuracy'],
        'precision': full_metrics['metrics']['precision'],
        'recall': full_metrics['metrics']['recall'],
        'f1_score': full_metrics['metrics']['f1'],
        'optimal_threshold': full_metrics['metrics_optimal_threshold']['threshold']
    }

    logger.info(f"  [OK] AUC={metrics['auc']:.4f}")
    return metrics

def calculate_statistics(all_metrics: list) -> dict:
    """
    Calculate stability statistics with 95% confidence intervals.

    Args:
        all_metrics: List of metrics dictionaries

    Returns:
        Statistics dictionary
    """
    aucs = [m['auc'] for m in all_metrics]
    pr_aucs = [m['pr_auc'] for m in all_metrics]
    accuracies = [m['accuracy'] for m in all_metrics]
    precisions = [m['precision'] for m in all_metrics]
    recalls = [m['recall'] for m in all_metrics]
    f1_scores = [m['f1_score'] for m in all_metrics]
    optimal_thresholds = [m['optimal_threshold'] for m in all_metrics]

    # Calculate 95% confidence interval for AUC
    auc_mean = np.mean(aucs)
    auc_std = np.std(aucs, ddof=1)
    auc_se = auc_std / np.sqrt(len(aucs))
    auc_ci = scipy_stats.t.interval(0.95, len(aucs)-1, loc=auc_mean, scale=auc_se)
    auc_ci_width = auc_ci[1] - auc_ci[0]

    stats = {
        'auc': {
            'mean': auc_mean,
            'std': auc_std,
            'min': np.min(aucs),
            'max': np.max(aucs),
            'cv': auc_std / auc_mean * 100,
            'ci_95_lower': auc_ci[0],
            'ci_95_upper': auc_ci[1],
            'ci_95_width': auc_ci_width
        },
        'pr_auc': {
            'mean': np.mean(pr_aucs),
            'std': np.std(pr_aucs, ddof=1)
        },
        'accuracy': {
            'mean': np.mean(accuracies),
            'std': np.std(accuracies, ddof=1)
        },
        'precision': {
            'mean': np.mean(precisions),
            'std': np.std(precisions, ddof=1)
        },
        'recall': {
            'mean': np.mean(recalls),
            'std': np.std(recalls, ddof=1),
            'cv': np.std(recalls, ddof=1) / np.mean(recalls) * 100
        },
        'f1_score': {
            'mean': np.mean(f1_scores),
            'std': np.std(f1_scores, ddof=1),
            'cv': np.std(f1_scores, ddof=1) / np.mean(f1_scores) * 100
        },
        'optimal_threshold': {
            'mean': np.mean(optimal_thresholds),
            'std': np.std(optimal_thresholds, ddof=1),
            'min': np.min(optimal_thresholds),
            'max': np.max(optimal_thresholds),
            'range_pct': (np.max(optimal_thresholds) - np.min(optimal_thresholds)) / np.mean(optimal_thresholds) * 100,
            'cv': np.std(optimal_thresholds, ddof=1) / np.mean(optimal_thresholds) * 100
        }
    }

    return stats


def assess_stability(stats: dict) -> str:
    """
    Assess stability level based on AUC statistics.

    Args:
        stats: Statistics dictionary

    Returns:
        Stability level (EXCELLENT, GOOD, ACCEPTABLE, POOR)
    """
    auc_std = stats['auc']['std']
    auc_cv = stats['auc']['cv']
    auc_ci_width = stats['auc']['ci_95_width']

    for level in ['EXCELLENT', 'GOOD', 'ACCEPTABLE']:
        criteria = STABILITY_CRITERIA[level]
        if (auc_std <= criteria['std'] and
            auc_cv <= criteria['cv'] and
            auc_ci_width <= criteria['ci_width']):
            return level

    return 'POOR'

def print_report(version: str, stats: dict, all_metrics: list, stability_level: str):
    """Print comprehensive stability report with assessment."""
    logger.info("=" * 80)
    logger.info(f"STABILITY VALIDATION REPORT - {version}")
    logger.info("=" * 80)
    logger.info(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Number of runs: {len(all_metrics)}")
    logger.info(f"Random seeds: {SEEDS}")
    logger.info("=" * 80)

    logger.info("\n1. AUC Stability")
    logger.info("-" * 80)
    logger.info(f"  Mean:       {stats['auc']['mean']:.4f}")
    logger.info(f"  Std:        {stats['auc']['std']:.4f}")
    logger.info(f"  Min:        {stats['auc']['min']:.4f}")
    logger.info(f"  Max:        {stats['auc']['max']:.4f}")
    logger.info(f"  CV:         {stats['auc']['cv']:.2f}%")
    logger.info(f"  95% CI:     [{stats['auc']['ci_95_lower']:.4f}, {stats['auc']['ci_95_upper']:.4f}]")
    logger.info(f"  CI Width:   {stats['auc']['ci_95_width']:.4f}")

    logger.info("\n2. Stability Assessment")
    logger.info("-" * 80)
    logger.info(f"  Level: {stability_level}")

    if stability_level == 'EXCELLENT':
        logger.info("  [OK] Model training is HIGHLY STABLE")
        logger.info("  Recommendation: Proceed with deployment")
    elif stability_level == 'GOOD':
        logger.info("  [OK] Model training is STABLE")
        logger.info("  Recommendation: Proceed with deployment")
    elif stability_level == 'ACCEPTABLE':
        logger.warning("  [WARNING] Model training stability is ACCEPTABLE but not ideal")
        logger.warning("  Recommendation: Consider further investigation before deployment")
    else:
        logger.error("  [FAIL] Model training is UNSTABLE")
        logger.error("  Recommendation: DO NOT deploy. Investigate root causes:")
        logger.error("    - Check data consistency")
        logger.error("    - Verify deterministic configuration")
        logger.error("    - Review hyperparameter sensitivity")

    logger.info("\n3. Optimal Threshold Stability")
    logger.info("-" * 80)
    logger.info(f"  Mean:  {stats['optimal_threshold']['mean']:.4f}")
    logger.info(f"  Std:   {stats['optimal_threshold']['std']:.4f}")
    logger.info(f"  Min:   {stats['optimal_threshold']['min']:.4f}")
    logger.info(f"  Max:   {stats['optimal_threshold']['max']:.4f}")
    logger.info(f"  Range: {stats['optimal_threshold']['range_pct']:.2f}%")
    logger.info(f"  CV:    {stats['optimal_threshold']['cv']:.2f}%")

    logger.info("\n4. Other Metrics")
    logger.info("-" * 80)
    logger.info(f"  Recall:    {stats['recall']['mean']:.4f} ± {stats['recall']['std']:.4f} (CV={stats['recall']['cv']:.2f}%)")
    logger.info(f"  F1 Score:  {stats['f1_score']['mean']:.4f} ± {stats['f1_score']['std']:.4f} (CV={stats['f1_score']['cv']:.2f}%)")

    logger.info("\n" + "=" * 80)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Stability validation for XGBoost model v2.6')
    parser.add_argument('--skip-hpo', action='store_true',
                        help='Skip Phase 1 (HPO) and use existing hyperparameters')
    args = parser.parse_args()

    version = 'v2_6'
    model_dir = Path(__file__).parent.parent / "models"
    hyperparams_path = model_dir / f"best_hyperparameters_{version}.json"

    # Phase 1: Hyperparameter Optimization (optional)
    if not args.skip_hpo:
        hyperparams_path = run_hpo_phase(version=version, seed=42)
    else:
        if not hyperparams_path.exists():
            logger.error(f"Hyperparameters file not found: {hyperparams_path}")
            logger.error("Please run Phase 1 first (without --skip-hpo)")
            sys.exit(1)
        logger.info(f"Using existing hyperparameters: {hyperparams_path}")

    # Phase 2: Fixed-Hyperparameter Stability Validation
    logger.info("=" * 80)
    logger.info(f"Phase 2: Fixed-Hyperparameter Stability Validation ({version})")
    logger.info("=" * 80)
    logger.info(f"Training with {len(SEEDS)} different random seeds...")
    logger.info("")

    all_metrics = []
    for seed in SEEDS:
        metrics = run_training_with_fixed_hyperparameters(version, seed, str(hyperparams_path))
        if metrics:
            all_metrics.append(metrics)

    if len(all_metrics) < len(SEEDS):
        logger.error(f"Only {len(all_metrics)}/{len(SEEDS)} runs succeeded. Aborting.")
        sys.exit(1)

    # Calculate statistics
    stats = calculate_statistics(all_metrics)
    stability_level = assess_stability(stats)

    # Print report
    print_report(version, stats, all_metrics, stability_level)

    # Save statistics
    output_path = model_dir / f"stability_stats_{version}.json"
    stats_with_metadata = {
        'statistics': stats,
        'stability_level': stability_level,
        'num_runs': len(all_metrics),
        'seeds': SEEDS,
        'generated_at': datetime.now().isoformat()
    }
    with open(output_path, 'w') as f:
        json.dump(stats_with_metadata, f, indent=2)
    logger.info(f"\n[OK] Statistics saved: {output_path}")

    # Exit with appropriate code
    if stability_level in ['EXCELLENT', 'GOOD']:
        sys.exit(0)
    elif stability_level == 'ACCEPTABLE':
        sys.exit(0)  # Still pass, but with warning
    else:
        sys.exit(1)  # Fail for POOR stability

