"""
Model v2 Diagnostic Script - Root Cause Analysis
Executes systematic diagnostics to identify why AUC=0.5026 (near random guess)
"""

import sys
import json
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from sklearn.metrics import roc_auc_score
import structlog

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from scripts.real_data_loader import RealDataLoader
from scripts.label_generator import LabelGenerator

logger = structlog.get_logger()

# Load trained model and metadata
MODEL_DIR = Path(__file__).parent.parent / "models"
model = joblib.load(MODEL_DIR / "xgboost_signal_confidence_v2.pkl")
with open(MODEL_DIR / "feature_names_v2.json", "r") as f:
    feature_names = json.load(f)
with open(MODEL_DIR / "model_metrics_v2.json", "r") as f:
    metadata = json.load(f)

logger.info("=" * 80)
logger.info("MODEL V2 DIAGNOSTIC REPORT - ROOT CAUSE ANALYSIS")
logger.info("=" * 80)
logger.info(f"Model version: {metadata['training_info']['model_version']}")
logger.info(f"Reported AUC: {metadata['metrics']['auc']:.4f}")
logger.info("")

# ============================================
# DIAGNOSTIC 1: Positive/Negative Class Direction Check
# ============================================
logger.info("=" * 80)
logger.info("DIAGNOSTIC 1: Positive/Negative Class Direction Check")
logger.info("=" * 80)

# Load validation data (reconstruct from training script logic)
from datetime import date

# Import FeatureEngineer from correct path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.services.feature_engineer import FeatureEngineer

symbols = metadata['training_info']['symbols']
start_date = date.fromisoformat(metadata['training_info']['start_date'])
end_date = date.fromisoformat(metadata['training_info']['end_date'])
lookback_periods = metadata['training_info']['lookback_periods']
future_window_hours = metadata['training_info']['future_window_hours']
bullish_threshold_pct = metadata['training_info']['bullish_threshold_pct']
bearish_threshold_pct = metadata['training_info']['bearish_threshold_pct']
train_ratio = 0.8

logger.info("Loading data for diagnostic...")
loader = RealDataLoader(db_url=settings.DATABASE_URL)
samples = loader.load_klines(
    symbols=symbols,
    interval='1h',
    start_date=start_date,
    end_date=end_date,
    lookback_periods=lookback_periods
)

label_gen = LabelGenerator(
    future_window_hours=future_window_hours,
    bullish_threshold_pct=bullish_threshold_pct,
    bearish_threshold_pct=bearish_threshold_pct
)

X = []
y = []
sample_metadata = []  # Store (symbol, timestamp) for later analysis

for window, symbol, timestamp, idx in samples:
    features = FeatureEngineer.calculate_features(window)
    if features is None:
        continue
    
    current_close = window[-1]['close']
    future_klines = loader.get_future_klines(
        symbol=symbol,
        interval='1h',
        start_timestamp=timestamp,
        num_periods=future_window_hours
    )
    
    label = label_gen.generate_label(current_close, future_klines)
    if label is not None:
        X.append(features)
        y.append(label)
        sample_metadata.append({
            'symbol': symbol,
            'timestamp': timestamp,
            'close': current_close
        })

X_df = pd.DataFrame(X, columns=feature_names)
y = np.array(y)

# Time-series split
split_idx = int(len(X_df) * train_ratio)
X_train, X_val = X_df.iloc[:split_idx], X_df.iloc[split_idx:]
y_train, y_val = y[:split_idx], y[split_idx:]
metadata_val = sample_metadata[split_idx:]

logger.info(f"Data loaded: {len(X_df)} total samples")
logger.info(f"Train: {len(X_train)}, Val: {len(X_val)}")
logger.info("")

# Predict on validation set
y_pred_proba = model.predict_proba(X_val)
y_pred = model.predict(X_val)

# Calculate AUC with both directions
auc_pos = roc_auc_score(y_val, y_pred_proba[:, 1])
auc_neg = roc_auc_score(y_val, 1 - y_pred_proba[:, 1])

# Calculate prediction statistics
pred_bullish_ratio = (y_pred == 1).mean()
train_bullish_ratio = (y_train == 1).mean()
val_bullish_ratio = (y_val == 1).mean()

logger.info("Positive/Negative Class Direction Check Results:")
logger.info(f"  - auc_pos (using y_pred_proba[:, 1]): {auc_pos:.4f}")
logger.info(f"  - auc_neg (using 1 - y_pred_proba[:, 1]): {auc_neg:.4f}")
logger.info(f"  - Predicted as Bullish ratio: {pred_bullish_ratio:.2%}")
logger.info(f"  - Train set Bullish ratio: {train_bullish_ratio:.2%}")
logger.info(f"  - Val set Bullish ratio: {val_bullish_ratio:.2%}")
logger.info("")

if auc_neg > auc_pos + 0.05:
    logger.error("❌ DIAGNOSIS: Positive/Negative class REVERSED or wrong probability column!")
    logger.error(f"   AUC with reversed probability ({auc_neg:.4f}) >> AUC with normal ({auc_pos:.4f})")
elif pred_bullish_ratio < 0.10:
    logger.warning("⚠️  DIAGNOSIS: Model is EXTREMELY CONSERVATIVE (predicts <10% as Bullish)")
    logger.warning("   This suggests severe class imbalance or threshold issues")
else:
    logger.info("✅ DIAGNOSIS: Positive/Negative class direction appears NORMAL")

logger.info("")

# ============================================
# DIAGNOSTIC 2: Label-Feature Time Alignment Check
# ============================================
logger.info("=" * 80)
logger.info("DIAGNOSTIC 2: Label-Feature Time Alignment Check")
logger.info("=" * 80)

# Sample 1000 random validation samples for alignment check
np.random.seed(42)
sample_indices = np.random.choice(len(metadata_val), min(1000, len(metadata_val)), replace=False)

alignment_pass = 0
alignment_fail = 0
sample_details = []

for i, idx in enumerate(sample_indices[:5]):  # Show first 5 samples in detail
    meta = metadata_val[idx]
    symbol = meta['symbol']
    t0 = meta['timestamp']
    current_close = meta['close']

    # Get future klines
    future_klines = loader.get_future_klines(
        symbol=symbol,
        interval='1h',
        start_timestamp=t0,
        num_periods=future_window_hours
    )

    if len(future_klines) == 0:
        continue

    # Check time alignment
    first_future_ts = future_klines[0]['open_time']

    # Calculate first hit timestamps
    bullish_price = current_close * (1 + bullish_threshold_pct / 100)
    bearish_price = current_close * (1 + bearish_threshold_pct / 100)

    up_hit_idx = next((i for i, k in enumerate(future_klines) if k['high'] >= bullish_price), None)
    down_hit_idx = next((i for i, k in enumerate(future_klines) if k['low'] <= bearish_price), None)

    first_up_ts = future_klines[up_hit_idx]['open_time'] if up_hit_idx is not None else None
    first_down_ts = future_klines[down_hit_idx]['open_time'] if down_hit_idx is not None else None

    # Determine label
    if up_hit_idx is not None and down_hit_idx is None:
        label = 1
    elif down_hit_idx is not None and up_hit_idx is None:
        label = 0
    else:
        label = None

    # Check alignment
    is_aligned = first_future_ts > t0
    if up_hit_idx is not None:
        is_aligned = is_aligned and (first_up_ts > t0)
    if down_hit_idx is not None:
        is_aligned = is_aligned and (first_down_ts > t0)

    if is_aligned:
        alignment_pass += 1
    else:
        alignment_fail += 1

    # Store sample details
    sample_details.append({
        'symbol': symbol,
        't0': t0.strftime('%Y-%m-%d %H:%M'),
        'close': f"{current_close:.2f}",
        'first_up_ts': first_up_ts.strftime('%Y-%m-%d %H:%M') if first_up_ts else 'None',
        'first_down_ts': first_down_ts.strftime('%Y-%m-%d %H:%M') if first_down_ts else 'None',
        'label': label,
        'aligned': is_aligned
    })

# Check all 1000 samples
for idx in sample_indices:
    meta = metadata_val[idx]
    symbol = meta['symbol']
    t0 = meta['timestamp']

    future_klines = loader.get_future_klines(
        symbol=symbol,
        interval='1h',
        start_timestamp=t0,
        num_periods=future_window_hours
    )

    if len(future_klines) > 0:
        first_future_ts = future_klines[0]['open_time']
        if first_future_ts > t0:
            alignment_pass += 1
        else:
            alignment_fail += 1

logger.info("Label-Feature Time Alignment Check Results (Random 5 samples):")
for detail in sample_details:
    logger.info(f"  Sample: symbol={detail['symbol']}, t0={detail['t0']}, close={detail['close']}")
    logger.info(f"          first_up_ts={detail['first_up_ts']}, first_down_ts={detail['first_down_ts']}, label={detail['label']}")
    logger.info(f"          aligned={detail['aligned']}")
    logger.info("")

logger.info(f"Alignment check on {len(sample_indices)} samples:")
logger.info(f"  - Assertions passed: {alignment_pass}")
logger.info(f"  - Assertions failed: {alignment_fail}")
logger.info("")

if alignment_fail > 0:
    logger.error("❌ DIAGNOSIS: Off-by-one ERROR detected in time alignment!")
else:
    logger.info("✅ DIAGNOSIS: Label-Feature time alignment is CORRECT")

logger.info("")

# ============================================
# DIAGNOSTIC 3: Train/Val Time Boundary Check
# ============================================
logger.info("=" * 80)
logger.info("DIAGNOSTIC 3: Train/Val Time Boundary Check")
logger.info("=" * 80)

# Group samples by symbol
train_metadata = sample_metadata[:split_idx]
val_metadata = sample_metadata[split_idx:]

symbol_stats = {}
for sym in symbols:
    train_sym = [m for m in train_metadata if m['symbol'] == sym]
    val_sym = [m for m in val_metadata if m['symbol'] == sym]

    if len(train_sym) > 0 and len(val_sym) > 0:
        train_times = [m['timestamp'] for m in train_sym]
        val_times = [m['timestamp'] for m in val_sym]

        train_labels = [y_train[i] for i, m in enumerate(train_metadata) if m['symbol'] == sym]
        val_labels = [y_val[i] for i, m in enumerate(val_metadata) if m['symbol'] == sym]

        symbol_stats[sym] = {
            'train_start': min(train_times),
            'train_end': max(train_times),
            'train_count': len(train_sym),
            'train_bullish_ratio': np.mean(train_labels),
            'val_start': min(val_times),
            'val_end': max(val_times),
            'val_count': len(val_sym),
            'val_bullish_ratio': np.mean(val_labels)
        }

logger.info("Train/Val Time Boundary Check Results:")
logger.info("")

max_bullish_diff = 0
for sym, stats in symbol_stats.items():
    logger.info(f"{sym}:")
    logger.info(f"  Train: [{stats['train_start'].strftime('%Y-%m-%d %H:%M')}, {stats['train_end'].strftime('%Y-%m-%d %H:%M')}], "
                f"samples={stats['train_count']}, Bullish={stats['train_bullish_ratio']:.1%}")
    logger.info(f"  Val:   [{stats['val_start'].strftime('%Y-%m-%d %H:%M')}, {stats['val_end'].strftime('%Y-%m-%d %H:%M')}], "
                f"samples={stats['val_count']}, Bullish={stats['val_bullish_ratio']:.1%}")

    bullish_diff = abs(stats['train_bullish_ratio'] - stats['val_bullish_ratio'])
    max_bullish_diff = max(max_bullish_diff, bullish_diff)
    logger.info("")

# Check if training set covers 2025 data
train_has_2025 = any(m['timestamp'].year == 2025 for m in train_metadata)

logger.info(f"Max Bullish ratio difference across symbols: {max_bullish_diff:.1%}")
logger.info(f"Training set covers 2025 data: {train_has_2025}")
logger.info("")

if max_bullish_diff > 0.10:
    logger.warning("⚠️  DIAGNOSIS: Train/Val Bullish ratio difference >10% detected!")
    logger.warning("   This suggests distribution shift between train and val sets")
elif not train_has_2025:
    logger.warning("⚠️  DIAGNOSIS: Training set does NOT cover 2025 data!")
    logger.warning("   Model may not generalize to 2025 market conditions")
else:
    logger.info("✅ DIAGNOSIS: Train/Val time boundaries appear NORMAL")

logger.info("")

# ============================================
# DIAGNOSTIC 4: Per-Symbol and Per-Year AUC Analysis
# ============================================
logger.info("=" * 80)
logger.info("DIAGNOSTIC 4: Per-Symbol and Per-Year AUC Analysis")
logger.info("=" * 80)

# Per-symbol AUC
logger.info("Per-Symbol AUC Analysis:")
logger.info("")

for sym in symbols:
    # Get validation samples for this symbol
    sym_indices = [i for i, m in enumerate(val_metadata) if m['symbol'] == sym]

    if len(sym_indices) < 10:
        logger.warning(f"{sym}: Insufficient validation samples ({len(sym_indices)}), skipping")
        continue

    y_val_sym = y_val[sym_indices]
    y_pred_proba_sym = y_pred_proba[sym_indices]

    # Calculate AUC
    if len(np.unique(y_val_sym)) < 2:
        logger.warning(f"{sym}: Only one class in validation set, cannot calculate AUC")
        continue

    auc_sym = roc_auc_score(y_val_sym, y_pred_proba_sym[:, 1])
    bullish_ratio_sym = np.mean(y_val_sym)

    # Calculate conflict rate (need to recalculate labels with conflict tracking)
    # For now, use overall conflict rate as approximation
    conflict_rate = metadata['training_info']['conflict_discarded'] / metadata['training_info']['total_raw_samples']

    logger.info(f"  {sym}: AUC={auc_sym:.4f}, samples={len(sym_indices)}, "
                f"Bullish={bullish_ratio_sym:.1%}, conflict_rate≈{conflict_rate:.1%}")

logger.info("")

# Per-year AUC
logger.info("Per-Year AUC Analysis:")
logger.info("")

year_2024_indices = [i for i, m in enumerate(val_metadata) if m['timestamp'].year == 2024]
year_2025_indices = [i for i, m in enumerate(val_metadata) if m['timestamp'].year == 2025]

if len(year_2024_indices) > 0:
    y_val_2024 = y_val[year_2024_indices]
    y_pred_proba_2024 = y_pred_proba[year_2024_indices]

    if len(np.unique(y_val_2024)) >= 2:
        auc_2024 = roc_auc_score(y_val_2024, y_pred_proba_2024[:, 1])
        bullish_ratio_2024 = np.mean(y_val_2024)
        logger.info(f"  2024: AUC={auc_2024:.4f}, samples={len(year_2024_indices)}, Bullish={bullish_ratio_2024:.1%}")
    else:
        logger.warning("  2024: Only one class in validation set, cannot calculate AUC")
else:
    logger.warning("  2024: No validation samples")

if len(year_2025_indices) > 0:
    y_val_2025 = y_val[year_2025_indices]
    y_pred_proba_2025 = y_pred_proba[year_2025_indices]

    if len(np.unique(y_val_2025)) >= 2:
        auc_2025 = roc_auc_score(y_val_2025, y_pred_proba_2025[:, 1])
        bullish_ratio_2025 = np.mean(y_val_2025)
        logger.info(f"  2025: AUC={auc_2025:.4f}, samples={len(year_2025_indices)}, Bullish={bullish_ratio_2025:.1%}")
    else:
        logger.warning("  2025: Only one class in validation set, cannot calculate AUC")
else:
    logger.warning("  2025: No validation samples")

logger.info("")

# Check for anomalies
min_symbol_auc = min([roc_auc_score(y_val[[i for i, m in enumerate(val_metadata) if m['symbol'] == sym]],
                                     y_pred_proba[[i for i, m in enumerate(val_metadata) if m['symbol'] == sym]][:, 1])
                      for sym in symbols
                      if len([i for i, m in enumerate(val_metadata) if m['symbol'] == sym]) >= 10
                      and len(np.unique(y_val[[i for i, m in enumerate(val_metadata) if m['symbol'] == sym]])) >= 2])

if min_symbol_auc < 0.45:
    logger.error(f"❌ DIAGNOSIS: At least one symbol has AUC << 0.5 (min={min_symbol_auc:.4f})")
    logger.error("   This symbol is severely dragging down overall performance")
elif len(year_2024_indices) > 0 and len(year_2025_indices) > 0:
    if len(np.unique(y_val_2024)) >= 2 and len(np.unique(y_val_2025)) >= 2:
        year_bullish_diff = abs(bullish_ratio_2024 - bullish_ratio_2025)
        if year_bullish_diff > 0.15:
            logger.warning(f"⚠️  DIAGNOSIS: Year-over-year Bullish ratio difference >15% ({year_bullish_diff:.1%})")
            logger.warning("   Market regime shift between 2024 and 2025")
        else:
            logger.info("✅ DIAGNOSIS: Per-symbol and per-year AUC appear NORMAL")
else:
    logger.info("✅ DIAGNOSIS: Per-symbol AUC analysis complete")

logger.info("")
logger.info("=" * 80)
logger.info("FIRST STAGE DIAGNOSTICS COMPLETE")
logger.info("=" * 80)


