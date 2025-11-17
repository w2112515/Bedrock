"""
XGBoost Model Training Script V2.6 - Multi-Frequency Features.

This script:
1. Loads real historical K-line data from PostgreSQL (1h + 4h)
2. Generates asymmetric three-class labels (bullish/bearish, discard neutral)
3. Calculates technical indicator features from multiple time frequencies
4. Trains XGBoost classifier with time-series split
5. Evaluates model performance
6. Saves model v2.6 and metadata

Key Improvements over V2.5:
- Multi-frequency features (1h + 4h technical indicators)
- Total 19 features (13 from 1h + 6 from 4h)
- Tests hypothesis: higher timeframe indicators improve prediction

Usage:
    python services/decision_engine/scripts/train_xgboost_v2_6.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import joblib
import json
import random
import argparse
import hashlib
from pathlib import Path
from datetime import date
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report,
    confusion_matrix,
    average_precision_score,
    precision_recall_curve
)
import xgboost as xgb
import pandas as pd
import structlog
import numpy as np

from services.decision_engine.scripts.real_data_loader import RealDataLoader
from services.decision_engine.scripts.label_generator import LabelGenerator
from services.decision_engine.app.services.feature_engineer import FeatureEngineer
from services.decision_engine.app.core.config import settings

# Setup logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer()
    ]
)
logger = structlog.get_logger()


def train_model_v2(
    symbols: list = None,
    start_date: date = date(2024, 1, 1),
    end_date: date = date(2025, 11, 15),
    lookback_periods: int = 100,
    future_window_hours: int = 24,
    bullish_threshold_pct: float = 1.0,  # EXPERIMENT 1: Lowered to +1.0%
    bearish_threshold_pct: float = -1.0,  # EXPERIMENT 1: Lowered to -1.0%
    train_ratio: float = 0.8,
    random_seed: int = 42,
    enable_hyperparameter_search: bool = True,
    n_random_search: int = 20,
    fixed_hyperparameters: dict = None
):
    """
    Train XGBoost model v2 using real historical data.

    Args:
        symbols: List of trading pairs (default: BTC, ETH, BNB, SOL, ADA)
        start_date: Training data start date
        end_date: Training data end date
        lookback_periods: Number of K-lines per sample
        future_window_hours: Future prediction window for labeling
        bullish_threshold_pct: Bullish label threshold (%)
        bearish_threshold_pct: Bearish label threshold (%)
        train_ratio: Training set ratio (0.8 = 80% train, 20% validation)
        random_seed: Random seed for reproducibility

    Returns:
        Dictionary of performance metrics
    """
    if symbols is None:
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]
    
    logger.info("=" * 80)
    logger.info("XGBoost Model Training V2 - Real Historical Data")
    logger.info("=" * 80)
    logger.info(f"Symbols: {symbols}")
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Lookback periods: {lookback_periods}")
    logger.info(f"Future window: {future_window_hours} hours")
    logger.info(f"Bullish threshold: +{bullish_threshold_pct}%")
    logger.info(f"Bearish threshold: {bearish_threshold_pct}%")
    logger.info(f"Train/Val split: {train_ratio:.0%} / {1-train_ratio:.0%}")
    logger.info("=" * 80)
    
    # ============================================
    # Step 1: Load Real Historical Data
    # ============================================
    logger.info("\nStep 1: Loading real historical K-line data (multi-frequency)...")

    loader = RealDataLoader(db_url=settings.DATABASE_URL)
    samples = loader.load_klines_multifreq(
        symbols=symbols,
        primary_interval="1h",
        secondary_interval="4h",
        start_date=start_date,
        end_date=end_date,
        lookback_periods=lookback_periods
    )
    
    logger.info(f"Loaded {len(samples)} raw samples")
    
    # ============================================
    # Step 2: Generate Labels and Calculate Features
    # ============================================
    logger.info("\nStep 2: Generating labels and calculating features...")
    
    label_gen = LabelGenerator(
        future_window_hours=future_window_hours,
        bullish_threshold_pct=bullish_threshold_pct,
        bearish_threshold_pct=bearish_threshold_pct
    )
    
    X = []
    y = []
    processed_count = 0
    
    for primary_window, secondary_window, symbol, timestamp, idx in samples:
        processed_count += 1

        if processed_count % 1000 == 0:
            logger.info(f"Processed {processed_count}/{len(samples)} samples...")

        # Calculate features (multi-frequency)
        features = FeatureEngineer.calculate_features_multifreq(primary_window, secondary_window)
        if not features:
            continue
        
        # Get future K-lines for labeling
        future_klines = loader.get_future_klines(
            symbol=symbol,
            interval="1h",
            start_timestamp=timestamp,
            num_periods=future_window_hours
        )

        # Generate label (use primary window's last close)
        current_close = primary_window[-1]['close']
        label = label_gen.generate_label(current_close, future_klines)

        # Skip neutral samples (label=None)
        if label is None:
            continue

        X.append(features)
        y.append(label)

    logger.info(f"Feature engineering complete: {len(X)} valid samples")

    # Print label statistics
    label_gen.print_statistics()

    # Convert to DataFrame
    X_df = pd.DataFrame(X)
    feature_names = X_df.columns.tolist()

    logger.info(f"Features: {len(feature_names)}")
    logger.info(f"Feature names: {feature_names}")
    logger.info(f"Class distribution: Bullish={sum(y)}, Bearish={len(y)-sum(y)}")

    # Check class balance
    bullish_ratio = sum(y) / len(y)
    logger.info(f"Bullish ratio: {bullish_ratio:.2%}")

    if bullish_ratio < 0.4 or bullish_ratio > 0.6:
        logger.warning(
            f"Class imbalance detected: bullish_ratio={bullish_ratio:.2%}. "
            "Consider adjusting thresholds."
        )

    # ============================================
    # Step 3: Time-Series Split (80% / 20%)
    # ============================================
    logger.info("\nStep 3: Splitting dataset (time-series split)...")

    # Calculate split index
    split_idx = int(len(X_df) * train_ratio)

    X_train = X_df.iloc[:split_idx]
    X_val = X_df.iloc[split_idx:]
    y_train = y[:split_idx]
    y_val = y[split_idx:]

    # Calculate data hash for consistency verification
    train_data_str = X_train.to_json(orient='values') + str(y_train)
    data_hash = hashlib.sha256(train_data_str.encode()).hexdigest()[:16]
    logger.info(f"Training data hash: {data_hash}")

    logger.info(f"Dataset split:")
    logger.info(f"  - Train: {len(X_train)} samples ({len(X_train)/len(X_df):.1%})")
    logger.info(f"  - Validation: {len(X_val)} samples ({len(X_val)/len(X_df):.1%})")
    logger.info(f"  - Train bullish ratio: {sum(y_train)/len(y_train):.2%}")
    logger.info(f"  - Val bullish ratio: {sum(y_val)/len(y_val):.2%}")

    # Calculate class imbalance weight (CRITICAL FIX for AUC=0.5026 issue)
    n_pos_train = sum(y_train)
    n_neg_train = len(y_train) - n_pos_train
    scale_pos_weight_base = n_neg_train / n_pos_train

    logger.info(f"\n[Class Imbalance Fix (STABILIZED)]:")
    logger.info(f"  - Positive samples (Bullish): {n_pos_train}")
    logger.info(f"  - Negative samples (Bearish): {n_neg_train}")
    logger.info(f"  - Fixed scale_pos_weight: {scale_pos_weight_base:.4f} (NOT searched)")
    logger.info(f"  - Stability measures: max_delta_step=1, gamma in [0.1,0.2], lr<=0.1")

    # ============================================
    # Step 4: Train XGBoost Model (with Hyperparameter Search)
    # ============================================
    logger.info("\nStep 4: Training XGBoost classifier...")

    best_params = None
    best_auc = 0.0

    # Use fixed hyperparameters if provided (for stability validation)
    if fixed_hyperparameters is not None:
        logger.info("Using fixed hyperparameters (stability validation mode)...")
        best_params = fixed_hyperparameters.copy()
        best_params['random_state'] = random_seed  # Only change random_state
        best_params['nthread'] = 1  # Single-threaded for determinism
        best_params['tree_method'] = 'hist'  # Use hist method (speed vs determinism tradeoff)
        enable_hyperparameter_search = False
        logger.info("Fixed hyperparameters:")
        for key, value in best_params.items():
            if key not in ['random_state', 'eval_metric', 'use_label_encoder']:
                logger.info(f"  - {key}: {value}")
    elif enable_hyperparameter_search:
        logger.info(f"Performing random hyperparameter search ({n_random_search} iterations)...")

        # Define hyperparameter search space (STABILIZED for class imbalance)
        # scale_pos_weight is FIXED and NOT searched to prevent instability
        param_space = {
            # Core stability parameters (CRITICAL for imbalanced data)
            'max_delta_step': [1],  # Fixed to 1: suppress extreme updates
            'learning_rate': [0.05, 0.075, 0.1],  # Reduced upper limit (was 0.15)
            'min_child_weight': [3, 5],  # Increased lower limit (was 1)
            'gamma': [0.1, 0.2],  # NEW: minimum loss reduction for split

            # Regularization parameters (STRENGTHENED)
            'reg_alpha': [0.1, 0.3],  # L1: increased lower limit (was 0)
            'reg_lambda': [2, 3],  # L2: increased lower limit (was 1)

            # Tree structure parameters (CONSERVATIVE)
            'max_depth': [3, 4, 5],  # Reduced upper limit (was 6)
            'n_estimators': [400, 600, 800],  # Increased to compensate for shallow trees

            # Sampling parameters (UNCHANGED)
            'subsample': [0.7, 0.8, 0.9],
            'colsample_bytree': [0.7, 0.8, 0.9]
        }

        # Split training set for hyperparameter validation (last 20% of train)
        hp_split_idx = int(len(X_train) * 0.8)
        X_hp_train = X_train.iloc[:hp_split_idx]
        X_hp_val = X_train.iloc[hp_split_idx:]
        y_hp_train = y_train[:hp_split_idx]
        y_hp_val = y_train[hp_split_idx:]

        logger.info(f"Hyperparameter validation split: {len(X_hp_train)} train, {len(X_hp_val)} val")

        # Random search
        for i in range(n_random_search):
            # Sample random hyperparameters
            params = {
                'max_depth': random.choice(param_space['max_depth']),
                'n_estimators': random.choice(param_space['n_estimators']),
                'learning_rate': random.choice(param_space['learning_rate']),
                'subsample': random.choice(param_space['subsample']),
                'colsample_bytree': random.choice(param_space['colsample_bytree']),
                'min_child_weight': random.choice(param_space['min_child_weight']),
                'reg_alpha': random.choice(param_space['reg_alpha']),
                'reg_lambda': random.choice(param_space['reg_lambda']),
                'gamma': random.choice(param_space['gamma']),  # NEW: split loss reduction
                'max_delta_step': random.choice(param_space['max_delta_step']),  # Fixed to 1
                'scale_pos_weight': scale_pos_weight_base,  # FIXED: not searched
                'random_state': random_seed,
                'eval_metric': ['auc', 'aucpr'],  # Monitor both ROC-AUC and PR-AUC
                'tree_method': 'hist',  # Faster histogram-based algorithm
                'use_label_encoder': False
            }

            # Train model
            model_hp = xgb.XGBClassifier(**params)
            model_hp.fit(
                X_hp_train,
                y_hp_train,
                eval_set=[(X_hp_val, y_hp_val)],
                early_stopping_rounds=50,
                verbose=False
            )

            # Evaluate on hyperparameter validation set
            y_hp_pred_proba = model_hp.predict_proba(X_hp_val)[:, 1]
            hp_auc = roc_auc_score(y_hp_val, y_hp_pred_proba)

            if hp_auc > best_auc:
                best_auc = hp_auc
                best_params = params
                logger.info(f"  Iteration {i+1}/{n_random_search}: AUC={hp_auc:.4f} [NEW BEST]")
            else:
                logger.info(f"  Iteration {i+1}/{n_random_search}: AUC={hp_auc:.4f}")

        logger.info(f"\nBest hyperparameters found (AUC={best_auc:.4f}):")
        for key, value in best_params.items():
            if key not in ['random_state', 'eval_metric', 'use_label_encoder']:
                logger.info(f"  - {key}: {value}")
    else:
        # Use default hyperparameters
        best_params = {
            'n_estimators': 100,
            'max_depth': 5,
            'learning_rate': 0.1,
            'random_state': random_seed,
            'eval_metric': 'auc',
            'use_label_encoder': False
        }
        logger.info("Using default hyperparameters (search disabled)")

    # Train final model on full training set with best hyperparameters
    logger.info("\nTraining final model on full training set...")
    model = xgb.XGBClassifier(**best_params)

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        early_stopping_rounds=100,
        verbose=False
    )

    logger.info("Training complete!")

    # ============================================
    # Step 5: Evaluate Model Performance
    # ============================================
    logger.info("\nStep 5: Evaluating model performance...")

    # Predictions
    y_pred = model.predict(X_val)
    y_pred_proba = model.predict_proba(X_val)[:, 1]

    # Calculate base metrics
    metrics = {
        'accuracy': float(accuracy_score(y_val, y_pred)),
        'precision': float(precision_score(y_val, y_pred)),
        'recall': float(recall_score(y_val, y_pred)),
        'f1': float(f1_score(y_val, y_pred)),
        'auc': float(roc_auc_score(y_val, y_pred_proba)),
        'pr_auc': float(average_precision_score(y_val, y_pred_proba))
    }

    # Calculate prediction distribution
    pred_bullish_ratio = float(y_pred.mean())

    # Find optimal threshold using F1 score
    precisions, recalls, thresholds = precision_recall_curve(y_val, y_pred_proba)
    f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-10)
    best_threshold_idx = np.argmax(f1_scores)
    best_threshold = float(thresholds[best_threshold_idx]) if best_threshold_idx < len(thresholds) else 0.5

    # Recalculate metrics with optimal threshold
    y_pred_optimal = (y_pred_proba >= best_threshold).astype(int)
    metrics_optimal = {
        'threshold': best_threshold,
        'accuracy': float(accuracy_score(y_val, y_pred_optimal)),
        'precision': float(precision_score(y_val, y_pred_optimal)),
        'recall': float(recall_score(y_val, y_pred_optimal)),
        'f1': float(f1_score(y_val, y_pred_optimal))
    }

    logger.info("=" * 80)
    logger.info("Model Performance Metrics (Validation Set)")
    logger.info("=" * 80)
    logger.info(f"ROC-AUC:       {metrics['auc']:.4f}")
    logger.info(f"PR-AUC:        {metrics['pr_auc']:.4f}")
    logger.info("")
    logger.info(f"Default Threshold (0.5):")
    logger.info(f"  Accuracy:    {metrics['accuracy']:.4f} ({metrics['accuracy']:.2%})")
    logger.info(f"  Precision:   {metrics['precision']:.4f} ({metrics['precision']:.2%})")
    logger.info(f"  Recall:      {metrics['recall']:.4f} ({metrics['recall']:.2%})")
    logger.info(f"  F1 Score:    {metrics['f1']:.4f} ({metrics['f1']:.2%})")
    logger.info(f"  Pred Bullish: {pred_bullish_ratio:.2%}")
    logger.info("")
    logger.info(f"Optimal Threshold ({metrics_optimal['threshold']:.4f}):")
    logger.info(f"  Accuracy:    {metrics_optimal['accuracy']:.4f} ({metrics_optimal['accuracy']:.2%})")
    logger.info(f"  Precision:   {metrics_optimal['precision']:.4f} ({metrics_optimal['precision']:.2%})")
    logger.info(f"  Recall:      {metrics_optimal['recall']:.4f} ({metrics_optimal['recall']:.2%})")
    logger.info(f"  F1 Score:    {metrics_optimal['f1']:.4f} ({metrics_optimal['f1']:.2%})")
    logger.info("=" * 80)

    # Confusion matrix
    cm = confusion_matrix(y_val, y_pred)
    logger.info("\nConfusion Matrix:")
    logger.info(f"                Predicted")
    logger.info(f"              Bearish  Bullish")
    logger.info(f"Actual Bearish   {cm[0][0]:5d}    {cm[0][1]:5d}")
    logger.info(f"       Bullish   {cm[1][0]:5d}    {cm[1][1]:5d}")

    # Classification report
    logger.info("\nClassification Report:")
    print(classification_report(y_val, y_pred, target_names=['Bearish', 'Bullish']))

    # Performance assessment (AUC-based gates)
    logger.info("\n" + "=" * 80)
    logger.info("[Performance Gate Assessment (AUC-Based)]")
    logger.info("=" * 80)

    if metrics['auc'] >= 0.60:
        logger.info("[OK] AUC >= 0.60: EXCELLENT - Ready for A/B test (30% traffic)")
        gate_status = "PASS_EXCELLENT"
    elif metrics['auc'] >= 0.58:
        logger.info("[WARN] AUC >= 0.58: ACCEPTABLE - A/B test with 48h monitoring")
        gate_status = "PASS_ACCEPTABLE"
    else:
        logger.error("[FAIL] AUC < 0.58: INSUFFICIENT - Do NOT deploy")
        gate_status = "FAIL"

    logger.info("")
    logger.info(f"Prediction Distribution Check:")
    logger.info(f"  - Train Bullish:     {sum(y_train)/len(y_train):.2%}")
    logger.info(f"  - Val Bullish:       {sum(y_val)/len(y_val):.2%}")
    logger.info(f"  - Predicted Bullish: {pred_bullish_ratio:.2%}")

    if pred_bullish_ratio < 0.10:
        logger.warning("  [WARN] Model is EXTREMELY CONSERVATIVE (<10% bullish predictions)")
    elif pred_bullish_ratio < 0.20:
        logger.warning("  [WARN] Model is CONSERVATIVE (<20% bullish predictions)")
    elif 0.20 <= pred_bullish_ratio <= 0.50:
        logger.info("  [OK] Prediction distribution is REASONABLE")
    else:
        logger.warning("  [WARN] Model is AGGRESSIVE (>50% bullish predictions)")

    logger.info("=" * 80)

    # ============================================
    # Step 6: Save Model V2 and Metadata
    # ============================================
    logger.info("\nStep 6: Saving model v2 and metadata...")

    # Create models directory
    model_dir = Path(__file__).parent.parent / "models"
    model_dir.mkdir(exist_ok=True)

    # Save model (with seed suffix)
    model_path = model_dir / f"xgboost_signal_confidence_v2_6_seed_{random_seed}.pkl"
    joblib.dump(model, model_path)
    logger.info(f"[OK] Model saved: {model_path}")

    # Save feature names (shared across all seeds)
    feature_names_path = model_dir / "feature_names_v2_6.json"
    with open(feature_names_path, 'w') as f:
        json.dump(feature_names, f, indent=2)
    logger.info(f"[OK] Feature names saved: {feature_names_path}")

    # Save performance metrics (with seed suffix)
    metrics_path = model_dir / f"model_metrics_v2_6_seed_{random_seed}.json"
    label_stats = label_gen.get_statistics()
    metrics_with_metadata = {
        'metrics': metrics,
        'metrics_optimal_threshold': metrics_optimal,
        'prediction_distribution': {
            'train_bullish_ratio': float(sum(y_train)/len(y_train)),
            'val_bullish_ratio': float(sum(y_val)/len(y_val)),
            'predicted_bullish_ratio': pred_bullish_ratio
        },
        'training_info': {
            'symbols': symbols,
            'start_date': str(start_date),
            'end_date': str(end_date),
            'lookback_periods': lookback_periods,
            'future_window_hours': future_window_hours,
            'bullish_threshold_pct': bullish_threshold_pct,
            'bearish_threshold_pct': bearish_threshold_pct,
            'num_features': len(feature_names),
            'train_size': len(X_train),
            'val_size': len(X_val),
            'total_raw_samples': len(samples),
            'valid_samples': label_stats['valid_samples'],
            'bullish_count': label_stats['bullish_count'],
            'bearish_count': label_stats['bearish_count'],
            'neutral_discarded': label_stats['neutral_count'],
            'conflict_discarded': label_stats['conflict_count'],
            'bullish_ratio': label_stats['bullish_ratio'],
            'scale_pos_weight_base': scale_pos_weight_base,
            'model_version': 'v2.6-multifreq',
            'data_source': 'real_historical',
            'random_seed': random_seed,
            'hyperparameter_search_enabled': enable_hyperparameter_search,
            'best_hyperparameters': {k: v for k, v in best_params.items() if k not in ['random_state', 'eval_metric', 'use_label_encoder']} if best_params else None,
            'gate_status': gate_status,
            'data_hash': data_hash  # For data consistency verification
        }
    }
    with open(metrics_path, 'w') as f:
        json.dump(metrics_with_metadata, f, indent=2)
    logger.info(f"[OK] Metrics saved: {metrics_path}")

    logger.info("\n" + "=" * 80)
    logger.info("Training Complete!")
    logger.info("=" * 80)
    logger.info(f"Model files saved to: {model_dir}")
    logger.info(f"  - {model_path.name}")
    logger.info(f"  - {feature_names_path.name}")
    logger.info(f"  - {metrics_path.name}")
    logger.info("=" * 80)

    return metrics


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Train XGBoost model v2.6 with multi-frequency features')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility (default: 42)')
    parser.add_argument('--fixed-hyperparameters', type=str, default=None,
                        help='Path to JSON file with fixed hyperparameters (for stability validation)')
    parser.add_argument('--disable-hpo', action='store_true',
                        help='Disable hyperparameter search (use default parameters)')
    args = parser.parse_args()

    # Set random seed globally
    random.seed(args.seed)
    np.random.seed(args.seed)

    logger.info(f"Using random seed: {args.seed}")

    # Load fixed hyperparameters if provided
    fixed_hyperparameters = None
    if args.fixed_hyperparameters:
        with open(args.fixed_hyperparameters, 'r') as f:
            fixed_hyperparameters = json.load(f)
        logger.info(f"Loaded fixed hyperparameters from: {args.fixed_hyperparameters}")

    # Determine if HPO should be enabled
    enable_hpo = not args.disable_hpo and fixed_hyperparameters is None

    metrics = train_model_v2(
        random_seed=args.seed,
        enable_hyperparameter_search=enable_hpo,
        fixed_hyperparameters=fixed_hyperparameters
    )

    # Exit with error code if performance is below threshold
    auc = metrics.get('auc', 0.0)

    if auc >= 0.60:
        logger.info(f"[OK] Model performance EXCELLENT (AUC={auc:.4f} >= 0.60). Success!")
        sys.exit(0)
    elif auc >= 0.58:
        logger.warning(f"[WARN] Model performance ACCEPTABLE (AUC={auc:.4f} >= 0.58). Recommend A/B testing with 30% traffic.")
        sys.exit(0)
    else:
        logger.error(f"[FAIL] Model performance INSUFFICIENT (AUC={auc:.4f} < 0.58). Entering diagnostic mode.")
        sys.exit(1)


