"""
XGBoost Model Training Script.

This script:
1. Generates synthetic training data
2. Calculates technical indicator features
3. Trains XGBoost classifier
4. Evaluates model performance
5. Saves model and metadata

Usage:
    python services/decision_engine/scripts/train_xgboost.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import joblib
import json
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, 
    precision_score, 
    recall_score, 
    f1_score, 
    roc_auc_score,
    classification_report
)
import xgboost as xgb
import structlog

from services.decision_engine.scripts.data_generator import MarketDataGenerator
from services.decision_engine.app.services.feature_engineer import FeatureEngineer

# Setup logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer()
    ]
)
logger = structlog.get_logger()


def train_model(
    num_samples: int = 2000,
    test_size: float = 0.3,
    random_state: int = 42
):
    """
    Train XGBoost model for signal confidence prediction.
    
    Args:
        num_samples: Number of synthetic samples to generate
        test_size: Proportion of data for validation + test (default: 0.3)
        random_state: Random seed for reproducibility
    
    Returns:
        Dictionary of performance metrics
    """
    logger.info("=" * 60)
    logger.info("XGBoost Model Training - Phase 2 ML Engine Integration")
    logger.info("=" * 60)
    
    # ============================================
    # Step 1: Generate Training Data (Task 2.1.2)
    # ============================================
    logger.info("Step 1: Generating synthetic training data...")
    generator = MarketDataGenerator(seed=random_state)
    samples = generator.generate_klines(
        num_samples=num_samples,
        lookback_periods=100
    )
    
    logger.info(f"Generated {len(samples)} samples")
    
    # ============================================
    # Step 2: Feature Engineering (Task 2.1.2)
    # ============================================
    logger.info("Step 2: Calculating technical indicator features...")
    X = []
    y = []
    
    for i, (klines, label) in enumerate(samples):
        features = FeatureEngineer.calculate_features(klines)
        
        if features:  # Only keep samples with successful feature calculation
            X.append(features)
            y.append(label)
        
        if (i + 1) % 200 == 0:
            logger.info(f"Processed {i + 1}/{len(samples)} samples")
    
    # Convert to DataFrame
    import pandas as pd
    X_df = pd.DataFrame(X)
    feature_names = X_df.columns.tolist()
    
    logger.info(f"Feature engineering complete:")
    logger.info(f"  - Total samples: {len(X_df)}")
    logger.info(f"  - Features: {len(feature_names)}")
    logger.info(f"  - Feature names: {feature_names}")
    logger.info(f"  - Class distribution: {pd.Series(y).value_counts().to_dict()}")
    
    # ============================================
    # Step 3: Split Dataset (70% / 15% / 15%)
    # ============================================
    logger.info("Step 3: Splitting dataset...")
    
    # First split: 70% train, 30% temp
    X_train, X_temp, y_train, y_temp = train_test_split(
        X_df, y, 
        test_size=test_size, 
        random_state=random_state,
        stratify=y
    )
    
    # Second split: 15% validation, 15% test
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp,
        test_size=0.5,
        random_state=random_state,
        stratify=y_temp
    )
    
    logger.info(f"Dataset split:")
    logger.info(f"  - Train: {len(X_train)} samples")
    logger.info(f"  - Validation: {len(X_val)} samples")
    logger.info(f"  - Test: {len(X_test)} samples")
    
    # ============================================
    # Step 4: Train XGBoost Model (Task 2.1.3)
    # ============================================
    logger.info("Step 4: Training XGBoost classifier...")
    
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=random_state,
        eval_metric='logloss',
        use_label_encoder=False
    )
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )
    
    logger.info("Training complete")
    
    # ============================================
    # Step 5: Evaluate Model (Task 2.1.4)
    # ============================================
    logger.info("Step 5: Evaluating model performance...")
    
    # Predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Calculate metrics
    metrics = {
        'accuracy': float(accuracy_score(y_test, y_pred)),
        'precision': float(precision_score(y_test, y_pred, zero_division=0)),
        'recall': float(recall_score(y_test, y_pred, zero_division=0)),
        'f1': float(f1_score(y_test, y_pred, zero_division=0)),
        'auc': float(roc_auc_score(y_test, y_pred_proba))
    }
    
    logger.info("=" * 60)
    logger.info("Model Performance Metrics:")
    logger.info("=" * 60)
    for metric_name, metric_value in metrics.items():
        logger.info(f"  {metric_name.upper()}: {metric_value:.4f} ({metric_value*100:.2f}%)")
    logger.info("=" * 60)
    
    # Classification report
    logger.info("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Bearish/Sideways', 'Bullish']))
    
    # Baseline performance note (Task 2.1.4)
    logger.info(f"\n✓ Baseline Accuracy Recorded: {metrics['accuracy']:.2%}")
    logger.info("  Note: This is a baseline model trained on synthetic data.")
    logger.info("  Performance will improve with real historical data in Phase 3.")
    
    # ============================================
    # Step 6: Save Model and Metadata (Task 2.1.5)
    # ============================================
    logger.info("\nStep 6: Saving model and metadata...")
    
    # Create models directory
    model_dir = Path(__file__).parent.parent / "models"
    model_dir.mkdir(exist_ok=True)
    
    # Save model
    model_path = model_dir / "xgboost_signal_confidence_v1.pkl"
    joblib.dump(model, model_path)
    logger.info(f"✓ Model saved: {model_path}")
    
    # Save feature names
    feature_names_path = model_dir / "feature_names.json"
    with open(feature_names_path, 'w') as f:
        json.dump(feature_names, f, indent=2)
    logger.info(f"✓ Feature names saved: {feature_names_path}")
    
    # Save performance metrics
    metrics_path = model_dir / "model_metrics.json"
    metrics_with_metadata = {
        'metrics': metrics,
        'training_info': {
            'num_samples': num_samples,
            'num_features': len(feature_names),
            'train_size': len(X_train),
            'val_size': len(X_val),
            'test_size': len(X_test),
            'model_version': 'v1',
            'data_source': 'synthetic',
            'random_state': random_state
        }
    }
    with open(metrics_path, 'w') as f:
        json.dump(metrics_with_metadata, f, indent=2)
    logger.info(f"✓ Metrics saved: {metrics_path}")
    
    # Save .gitkeep to ensure models directory is tracked
    gitkeep_path = model_dir / ".gitkeep"
    gitkeep_path.touch()
    
    logger.info("\n" + "=" * 60)
    logger.info("Training Complete!")
    logger.info("=" * 60)
    logger.info(f"Model files saved to: {model_dir}")
    logger.info(f"  - {model_path.name}")
    logger.info(f"  - {feature_names_path.name}")
    logger.info(f"  - {metrics_path.name}")
    
    return metrics


def main():
    """Main entry point."""
    try:
        metrics = train_model(
            num_samples=2000,
            test_size=0.3,
            random_state=42
        )
        
        logger.info("\n✓ Training script completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())

