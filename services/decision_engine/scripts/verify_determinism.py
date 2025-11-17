"""
Determinism Verification Script.

This script verifies that the training process is deterministic by:
1. Running training twice with the same random seed
2. Comparing the AUC scores to ensure they are identical (diff < 1e-6)
3. Reporting whether determinism is achieved

Usage:
    python services/decision_engine/scripts/verify_determinism.py --version v2_7 --seed 42
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import subprocess
import json
import argparse
from pathlib import Path
import structlog

# Setup logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer()
    ]
)
logger = structlog.get_logger()


def run_training(version: str, seed: int, run_id: int, fixed_hyperparameters: str = None) -> dict:
    """
    Run training script and return metrics.
    
    Args:
        version: Model version (v2_6 or v2_7)
        seed: Random seed
        run_id: Run identifier (1 or 2)
        fixed_hyperparameters: Path to fixed hyperparameters JSON
        
    Returns:
        Dictionary of metrics
    """
    logger.info(f"Running training (version={version}, seed={seed}, run={run_id})...")
    
    script_name = f"train_xgboost_{version}.py"
    cmd = ["python", f"services/decision_engine/scripts/{script_name}", "--seed", str(seed)]
    
    if fixed_hyperparameters:
        cmd.extend(["--fixed-hyperparameters", fixed_hyperparameters])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        logger.error(f"Training failed: {result.stderr}")
        raise RuntimeError(f"Training failed for {version} seed={seed} run={run_id}")
    
    # Load metrics
    model_dir = Path(__file__).parent.parent / "models"
    metrics_path = model_dir / f"model_metrics_{version}_seed_{seed}.json"
    
    with open(metrics_path, 'r') as f:
        data = json.load(f)
    
    return data['metrics']


def verify_determinism(version: str, seed: int = 42, fixed_hyperparameters: str = None) -> bool:
    """
    Verify determinism by running training twice with the same seed.
    
    Args:
        version: Model version (v2_6 or v2_7)
        seed: Random seed
        fixed_hyperparameters: Path to fixed hyperparameters JSON
        
    Returns:
        True if determinism is verified, False otherwise
    """
    logger.info("=" * 80)
    logger.info(f"Determinism Verification for {version}")
    logger.info("=" * 80)
    logger.info(f"Random seed: {seed}")
    if fixed_hyperparameters:
        logger.info(f"Fixed hyperparameters: {fixed_hyperparameters}")
    logger.info("")
    
    # Run training twice
    metrics1 = run_training(version, seed, run_id=1, fixed_hyperparameters=fixed_hyperparameters)
    metrics2 = run_training(version, seed, run_id=2, fixed_hyperparameters=fixed_hyperparameters)
    
    # Compare AUC scores
    auc1 = metrics1['auc']
    auc2 = metrics2['auc']
    auc_diff = abs(auc1 - auc2)
    
    logger.info("")
    logger.info("Results:")
    logger.info(f"  Run 1 AUC: {auc1:.10f}")
    logger.info(f"  Run 2 AUC: {auc2:.10f}")
    logger.info(f"  Difference: {auc_diff:.10f}")
    logger.info("")
    
    if auc_diff < 1e-6:
        logger.info("[OK] DETERMINISM VERIFIED: AUC difference < 1e-6")
        logger.info("The training process is deterministic with the current configuration.")
        return True
    else:
        logger.error("[FAIL] DETERMINISM FAILED: AUC difference >= 1e-6")
        logger.error("Possible causes:")
        logger.error("  - Multi-threading not fully disabled (check nthread=1)")
        logger.error("  - tree_method='hist' may have non-deterministic behavior")
        logger.error("  - Data loading order inconsistent")
        logger.error("  - Random seed not properly set")
        logger.error("")
        logger.error("Recommendations:")
        logger.error("  1. Ensure nthread=1 in XGBoost parameters")
        logger.error("  2. Consider using tree_method='exact' for absolute determinism")
        logger.error("  3. Verify data loading order is consistent")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Verify training determinism')
    parser.add_argument('--version', type=str, required=True, choices=['v2_6', 'v2_7'],
                        help='Model version to verify')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed (default: 42)')
    parser.add_argument('--fixed-hyperparameters', type=str, default=None,
                        help='Path to fixed hyperparameters JSON')
    args = parser.parse_args()
    
    success = verify_determinism(args.version, args.seed, args.fixed_hyperparameters)
    
    sys.exit(0 if success else 1)

