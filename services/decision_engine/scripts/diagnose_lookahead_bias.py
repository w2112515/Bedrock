"""
Look-Ahead Bias Diagnostic Tool

Detects potential look-ahead bias (future information leakage) in feature-label alignment.
This is the most likely root cause of AUC stuck at ~0.50.

Three critical checks:
1. Feature window must NOT include current K-line (window_end < current_time)
2. Label calculation must NOT include current K-line (future_start > current_time)
3. Feature window and label window must NOT overlap
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from services.decision_engine.scripts.real_data_loader import RealDataLoader
from services.decision_engine.scripts.label_generator import LabelGenerator
from datetime import datetime, timedelta
import random
import structlog

logger = structlog.get_logger()


def diagnose_lookahead_bias(num_samples=10):
    """
    Diagnose look-ahead bias: check feature-label time alignment
    
    Checks:
    1. Feature window's last K-line time < current time (cannot include current K-line)
    2. Label calculation's future window start time > current time (cannot include current K-line)
    3. No overlap between feature window and label window
    """
    logger.info("=" * 80)
    logger.info("Look-Ahead Bias Diagnostic Tool")
    logger.info("=" * 80)

    # Load data
    db_url = "postgresql://bedrock:bedrock_password@localhost:5432/bedrock_db"
    loader = RealDataLoader(db_url=db_url)
    samples = loader.load_klines(
        symbols=['BTCUSDT'],
        interval='1h',
        start_date=datetime(2024, 6, 1).date(),
        end_date=datetime(2024, 6, 30).date(),
        lookback_periods=100
    )
    
    logger.info(f"Loaded {len(samples)} samples for diagnosis")
    
    # Random sample selection
    selected_samples = random.sample(samples, min(num_samples, len(samples)))
    
    label_gen = LabelGenerator(
        future_window_hours=24,
        bullish_threshold_pct=2.0,
        bearish_threshold_pct=-1.5
    )
    
    issues_found = 0
    
    for i, (klines_window, symbol, current_timestamp, index) in enumerate(selected_samples, 1):
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Sample {i}/{num_samples}")
        logger.info(f"{'=' * 80}")
        
        # Check 1: Window boundary
        window_start_time = klines_window[0]['timestamp']
        window_end_time = klines_window[-1]['timestamp']
        current_close = klines_window[-1]['close']
        
        logger.info(f"Current timestamp:     {current_timestamp}")
        logger.info(f"Window start:          {window_start_time}")
        logger.info(f"Window end:            {window_end_time}")
        logger.info(f"Window size:           {len(klines_window)} K-lines")
        
        # ⚠️ CRITICAL CHECK: Window end time must be < current time
        if window_end_time >= current_timestamp:
            logger.error(f"❌ LOOK-AHEAD BIAS DETECTED: Window end time ({window_end_time}) >= Current time ({current_timestamp})")
            logger.error(f"   This means features are calculated using the current K-line, which leaks future information!")
            issues_found += 1
        else:
            time_gap = (current_timestamp - window_end_time).total_seconds() / 3600
            logger.info(f"✅ Window boundary OK: {time_gap:.1f} hours gap between window end and current time")
        
        # Check 2: Get future K-lines for label generation
        future_klines = loader.get_future_klines(
            symbol=symbol,
            interval='1h',
            start_timestamp=current_timestamp,
            num_periods=24
        )
        
        if len(future_klines) < 24:
            logger.warning(f"⚠️  Insufficient future data: {len(future_klines)}/24 K-lines")
            continue
        
        # Check future window start time
        # Note: get_future_klines returns 'open_time' (milliseconds timestamp)
        future_start_time = datetime.fromtimestamp(future_klines[0]['open_time'] / 1000)
        future_end_time = datetime.fromtimestamp(future_klines[-1]['open_time'] / 1000)
        
        logger.info(f"Future window start:   {future_start_time}")
        logger.info(f"Future window end:     {future_end_time}")
        
        # ⚠️ CRITICAL CHECK: Future window start must be > current time
        if future_start_time <= current_timestamp:
            logger.error(f"❌ LABEL LEAKAGE DETECTED: Future window start ({future_start_time}) <= Current time ({current_timestamp})")
            logger.error(f"   This means label calculation includes the current K-line!")
            issues_found += 1
        else:
            logger.info(f"✅ Future window boundary OK: starts after current time")
        
        # Check 3: Generate label and verify calculation logic
        label = label_gen.generate_label(current_close, future_klines)
        
        # Manual label verification
        bullish_threshold = current_close * 1.02
        bearish_threshold = current_close * 0.985
        
        future_highs = [k['high'] for k in future_klines]
        future_lows = [k['low'] for k in future_klines]
        max_high = max(future_highs)
        min_low = min(future_lows)
        
        logger.info(f"\nLabel Calculation:")
        logger.info(f"  Current close:        {current_close:.2f}")
        logger.info(f"  Bullish threshold:    {bullish_threshold:.2f} (+2.0%)")
        logger.info(f"  Bearish threshold:    {bearish_threshold:.2f} (-1.5%)")
        logger.info(f"  Future max high:      {max_high:.2f}")
        logger.info(f"  Future min low:       {min_low:.2f}")
        logger.info(f"  Generated label:      {label} ({'Bullish' if label == 1 else 'Bearish' if label == 0 else 'Neutral'})")

        # ⚠️ CRITICAL CHECK: Verify label calculation doesn't use current K-line's high/low
        current_high = klines_window[-1]['high']
        current_low = klines_window[-1]['low']

        if max_high == current_high or min_low == current_low:
            logger.error(f"❌ LABEL CALCULATION ERROR: Using current K-line's high/low in label calculation!")
            logger.error(f"   Current high: {current_high:.2f}, Future max high: {max_high:.2f}")
            logger.error(f"   Current low: {current_low:.2f}, Future min low: {min_low:.2f}")
            issues_found += 1
        else:
            logger.info(f"✅ Label calculation OK: not using current K-line data")

    # Summary
    logger.info(f"\n{'=' * 80}")
    logger.info(f"Diagnosis Summary")
    logger.info(f"{'=' * 80}")
    logger.info(f"Samples checked: {num_samples}")
    logger.info(f"Issues found: {issues_found}")

    if issues_found > 0:
        logger.error(f"\n❌ LOOK-AHEAD BIAS CONFIRMED: {issues_found} issue(s) detected")
        logger.error(f"   This explains why AUC is stuck at ~0.50")
        logger.error(f"   FIX REQUIRED before any further training")
        return False
    else:
        logger.info(f"\n✅ NO LOOK-AHEAD BIAS DETECTED")
        logger.info(f"   Time alignment appears correct")
        logger.info(f"   The AUC issue may be due to other factors (feature quality, task difficulty, etc.)")
        return True


if __name__ == "__main__":
    is_clean = diagnose_lookahead_bias(num_samples=10)
    sys.exit(0 if is_clean else 1)

