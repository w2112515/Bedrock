"""
Data Consistency Verification Script.

This script verifies that all training runs use identical training data by:
1. Loading data_hash from all metrics files
2. Checking if all hashes are identical
3. Reporting any inconsistencies

Usage:
    python services/decision_engine/scripts/verify_data_consistency.py --version v2_7
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

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

# Default seeds used in stability validation
DEFAULT_SEEDS = [42, 123, 456, 789, 1024, 2048, 3141, 5926, 2718, 2024]


def verify_data_consistency(version: str, seeds: list = None) -> bool:
    """
    Verify that all training runs use identical training data.
    
    Args:
        version: Model version (v2_6 or v2_7)
        seeds: List of random seeds to check
        
    Returns:
        True if all data hashes are identical, False otherwise
    """
    if seeds is None:
        seeds = DEFAULT_SEEDS
    
    logger.info("=" * 80)
    logger.info(f"Data Consistency Verification for {version}")
    logger.info("=" * 80)
    logger.info(f"Checking {len(seeds)} training runs...")
    logger.info("")
    
    model_dir = Path(__file__).parent.parent / "models"
    hashes = []
    missing_files = []
    
    # Load data hashes from all metrics files
    for seed in seeds:
        metrics_path = model_dir / f"model_metrics_{version}_seed_{seed}.json"
        
        if not metrics_path.exists():
            missing_files.append(seed)
            logger.warning(f"  Seed {seed}: metrics file not found")
            continue
        
        with open(metrics_path, 'r') as f:
            data = json.load(f)
        
        data_hash = data['training_info'].get('data_hash', 'N/A')
        hashes.append((seed, data_hash))
        logger.info(f"  Seed {seed}: data_hash = {data_hash}")
    
    logger.info("")
    
    # Check if any files are missing
    if missing_files:
        logger.error(f"[FAIL] Missing metrics files for seeds: {missing_files}")
        logger.error("Please run training for all seeds before verifying data consistency.")
        return False

    # Check if all hashes are identical
    unique_hashes = set(h for _, h in hashes)

    if len(unique_hashes) == 1:
        logger.info("[OK] DATA CONSISTENCY VERIFIED")
        logger.info(f"All {len(hashes)} training runs use identical training data.")
        logger.info(f"Common data_hash: {list(unique_hashes)[0]}")
        return True
    else:
        logger.error("[FAIL] DATA CONSISTENCY FAILED")
        logger.error(f"Found {len(unique_hashes)} different data hashes:")
        for i, unique_hash in enumerate(unique_hashes, 1):
            seeds_with_hash = [seed for seed, h in hashes if h == unique_hash]
            logger.error(f"  Hash {i}: {unique_hash}")
            logger.error(f"    Seeds: {seeds_with_hash}")
        logger.error("")
        logger.error("Possible causes:")
        logger.error("  - Data loading order is inconsistent")
        logger.error("  - Database was updated between training runs")
        logger.error("  - Different data filtering logic applied")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Verify data consistency across training runs')
    parser.add_argument('--version', type=str, required=True, choices=['v2_6', 'v2_7'],
                        help='Model version to verify')
    parser.add_argument('--seeds', type=int, nargs='+', default=None,
                        help='List of seeds to check (default: standard 10 seeds)')
    args = parser.parse_args()
    
    success = verify_data_consistency(args.version, args.seeds)
    
    sys.exit(0 if success else 1)

