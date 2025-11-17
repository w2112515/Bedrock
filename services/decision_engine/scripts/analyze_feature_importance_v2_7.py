"""
Feature Importance Analysis for XGBoost Model v2.7 - Cross-Pair Features.

This script:
1. Loads all 10 trained v2.7 models
2. Extracts feature importance from each model
3. Calculates average importance and stability
4. Identifies top cross-pair features
5. Generates comprehensive feature importance report

Usage:
    python services/decision_engine/scripts/analyze_feature_importance_v2_7.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import pickle
import json
import numpy as np
from pathlib import Path
from typing import Dict, List

# Random seeds used in stability validation
SEEDS = [42, 123, 456, 789, 1024, 2048, 3141, 5926, 2718, 2024]

# Cross-pair feature names
CROSSPAIR_FEATURES = [
    'btc_return_1h_lag',
    'btc_return_2h_lag',
    'btc_return_4h_lag',
    'btc_return_24h_lag',
    'btc_trend_4h',
    'eth_return_1h_lag',
    'eth_return_2h_lag',
    'market_return_1h',
    'market_bullish_ratio',
    'btc_eth_corr_24h',
    'btc_target_corr_24h'
]

def load_model(seed: int):
    """Load trained model for given seed."""
    model_path = Path(__file__).parent.parent / "models" / f"xgboost_signal_confidence_v2_7_seed_{seed}.pkl"
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    return model

def load_feature_names() -> List[str]:
    """Load feature names."""
    feature_path = Path(__file__).parent.parent / "models" / "feature_names_v2_7.json"
    with open(feature_path, 'r') as f:
        feature_names = json.load(f)
    return feature_names

def extract_feature_importance(model, feature_names: List[str]) -> Dict[str, float]:
    """Extract feature importance from model using feature_importances_ attribute."""
    # Use feature_importances_ attribute (default: 'weight' importance type)
    importance_array = model.feature_importances_

    # Map to feature names
    feature_importance = {name: importance_array[i] for i, name in enumerate(feature_names)}

    # Normalize to sum to 1.0
    total = sum(feature_importance.values())
    if total > 0:
        feature_importance = {k: v / total for k, v in feature_importance.items()}

    return feature_importance

def calculate_statistics(all_importances: List[Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    """Calculate mean and std for each feature."""
    feature_names = all_importances[0].keys()
    stats = {}
    
    for feature in feature_names:
        values = [imp[feature] for imp in all_importances]
        stats[feature] = {
            'mean': np.mean(values),
            'std': np.std(values, ddof=1),
            'min': np.min(values),
            'max': np.max(values),
            'cv': np.std(values, ddof=1) / np.mean(values) * 100 if np.mean(values) > 0 else 0
        }
    
    return stats

def print_report(stats: Dict[str, Dict[str, float]], feature_names: List[str]):
    """Print comprehensive feature importance report."""
    print("\n" + "="*80)
    print("FEATURE IMPORTANCE ANALYSIS - v2.7-cross-pair")
    print("="*80)
    print(f"Number of models: {len(SEEDS)}")
    print(f"Total features: {len(feature_names)}")
    print(f"Cross-pair features: {len(CROSSPAIR_FEATURES)}")
    print("="*80)
    
    # Sort by mean importance
    sorted_features = sorted(stats.items(), key=lambda x: x[1]['mean'], reverse=True)
    
    print("\n1. Top 15 Most Important Features")
    print("-" * 80)
    print(f"{'Rank':<6} {'Feature':<30} {'Mean':<10} {'Std':<10} {'CV':<10} {'Type':<15}")
    print("-" * 80)
    
    for rank, (feature, stat) in enumerate(sorted_features[:15], 1):
        feature_type = "Cross-Pair" if feature in CROSSPAIR_FEATURES else "Multi-Freq"
        print(f"{rank:<6} {feature:<30} {stat['mean']:.6f}  {stat['std']:.6f}  {stat['cv']:>6.2f}%  {feature_type:<15}")
    
    print("\n2. Cross-Pair Features Ranking")
    print("-" * 80)
    print(f"{'Rank':<6} {'Feature':<30} {'Mean':<10} {'Std':<10} {'CV':<10}")
    print("-" * 80)
    
    crosspair_stats = [(f, stats[f]) for f in CROSSPAIR_FEATURES]
    crosspair_stats.sort(key=lambda x: x[1]['mean'], reverse=True)
    
    for rank, (feature, stat) in enumerate(crosspair_stats, 1):
        print(f"{rank:<6} {feature:<30} {stat['mean']:.6f}  {stat['std']:.6f}  {stat['cv']:>6.2f}%")
    
    # Calculate total importance of cross-pair features
    total_crosspair = sum(stats[f]['mean'] for f in CROSSPAIR_FEATURES)
    total_multifreq = sum(stats[f]['mean'] for f in feature_names if f not in CROSSPAIR_FEATURES)
    
    print("\n3. Feature Category Contribution")
    print("-" * 80)
    print(f"Multi-Freq Features (19):  {total_multifreq:.4f} ({total_multifreq*100:.2f}%)")
    print(f"Cross-Pair Features (11):  {total_crosspair:.4f} ({total_crosspair*100:.2f}%)")
    print(f"Total:                     {total_multifreq + total_crosspair:.4f}")
    
    print("\n4. Feature Stability Analysis")
    print("-" * 80)
    
    # Find most stable features (low CV)
    stable_features = sorted(stats.items(), key=lambda x: x[1]['cv'])[:10]
    print("\nMost Stable Features (Low CV):")
    for rank, (feature, stat) in enumerate(stable_features, 1):
        feature_type = "Cross-Pair" if feature in CROSSPAIR_FEATURES else "Multi-Freq"
        print(f"  {rank}. {feature:<30} CV={stat['cv']:>6.2f}%  ({feature_type})")
    
    # Find most unstable features (high CV)
    unstable_features = sorted(stats.items(), key=lambda x: x[1]['cv'], reverse=True)[:10]
    print("\nMost Unstable Features (High CV):")
    for rank, (feature, stat) in enumerate(unstable_features, 1):
        feature_type = "Cross-Pair" if feature in CROSSPAIR_FEATURES else "Multi-Freq"
        print(f"  {rank}. {feature:<30} CV={stat['cv']:>6.2f}%  ({feature_type})")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    print("Loading models and extracting feature importance...")
    
    feature_names = load_feature_names()
    all_importances = []
    
    for seed in SEEDS:
        model = load_model(seed)
        importance = extract_feature_importance(model, feature_names)
        all_importances.append(importance)
        print(f"  [OK] Loaded model seed={seed}")
    
    print("\nCalculating statistics...")
    stats = calculate_statistics(all_importances)
    
    print_report(stats, feature_names)
    
    # Save statistics
    output_path = Path(__file__).parent.parent / "models" / "feature_importance_v2_7.json"
    with open(output_path, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"\n[OK] Feature importance saved: {output_path}")

