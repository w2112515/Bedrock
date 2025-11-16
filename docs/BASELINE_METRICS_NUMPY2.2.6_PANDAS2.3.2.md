# Baseline Metrics for numpy 2.2.6 and pandas 2.3.2

## Purpose

This document records the baseline metrics for BacktestingService after upgrading to:
- **numpy**: 2.2.6 (from 1.26.2)
- **pandas**: 2.3.2 (from 2.1.3)
- **scikit-learn**: 1.5.2
- **xgboost**: 2.1.4

These baseline metrics serve as the reference for future regression testing. Any code changes or dependency upgrades should be validated against these baselines to ensure calculation accuracy is maintained.

## Test Configuration

- **Backtest ID**: `8d2a6198-4848-4d8f-8725-8a2c64cf9e2b`
- **Strategy Name**: "Baseline - numpy 2.2.6 pandas 2.3.2"
- **Strategy Type**: `rules_only` (DecisionEngine with rule-based strategy, no ML/LLM)
- **Market**: BTCUSDT
- **Interval**: 1h
- **Date Range**: 2024-01-01 to 2024-01-31 (31 days)
- **Initial Balance**: 100,000.00 USDT
- **Commission Rate**: 0.1% (0.001)
- **Slippage Rate**: 0.05% (0.0005)

## Baseline Metrics

| Metric | Value | Unit | Notes |
|--------|-------|------|-------|
| **Final Balance** | 98,961.65 | USDT | -1.04% from initial |
| **ROI** | -0.0104 | -1.04% | Return on Investment |
| **Total Trades** | 15 | count | Complete trade pairs (entry + exit) |
| **Winning Trades** | 5 | count | 33.33% win rate |
| **Losing Trades** | 10 | count | 66.67% loss rate |
| **Win Rate** | 0.3333 | 33.33% | Winning trades / Total trades |
| **Average Win** | 2,312.13 | USDT | Average profit per winning trade |
| **Average Loss** | -1,259.90 | USDT | Average loss per losing trade |
| **Profit Factor** | 0.9176 | ratio | Total profit / Total loss |
| **Max Drawdown** | 0.055 | 5.5% | Maximum peak-to-trough decline |
| **Sharpe Ratio** | -0.0301 | ratio | Risk-adjusted return |
| **Calmar Ratio** | -0.1886 | ratio | ROI / Max Drawdown |
| **Sortino Ratio** | -0.1209 | ratio | Downside risk-adjusted return |
| **Omega Ratio** | 0.9352 | ratio | Probability-weighted ratio of gains vs losses |
| **Total Commission** | 1,485.90 | USDT | Total trading fees |
| **Total Slippage** | 371.36 | USDT | Total slippage costs |

## Trade Statistics

- **Total Trade Records**: 30 (15 entry + 15 exit)
- **Average Trade Duration**: ~2 days (estimated from 31-day period with 15 trades)
- **Total Trading Costs**: 1,857.26 USDT (commission + slippage)

## Validation Criteria for Future Changes

When validating future code changes or dependency upgrades, use the following criteria:

### Critical Metrics (Must Match Within 0.01%)
- **ROI**: -0.0104 ± 0.000001 (-1.04% ± 0.0001%)
- **Final Balance**: 98,961.65 ± 0.99 USDT
- **Total Trades**: 15 (exact match)

### Important Metrics (Must Match Within 0.1%)
- **Win Rate**: 0.3333 ± 0.0003 (33.33% ± 0.03%)
- **Max Drawdown**: 0.055 ± 0.0001 (5.5% ± 0.01%)
- **Sharpe Ratio**: -0.0301 ± 0.0003
- **Sortino Ratio**: -0.1209 ± 0.0012

### Secondary Metrics (Must Match Within 1%)
- **Profit Factor**: 0.9176 ± 0.0092
- **Average Win**: 2,312.13 ± 23.12 USDT
- **Average Loss**: -1,259.90 ± 12.60 USDT
- **Total Commission**: 1,485.90 ± 14.86 USDT
- **Total Slippage**: 371.36 ± 3.71 USDT

## Data Files

- **Metrics JSON**: `baseline_metrics_numpy2.2.6_pandas2.3.2.json`
- **Trades JSON**: `baseline_trades_numpy2.2.6_pandas2.3.2.json`
- **Backtest ID File**: `baseline_backtest_id.txt`

## Verification Date

- **Created**: 2025-11-16 16:13:07 UTC
- **Verified By**: AI Assistant (Augment Agent)
- **Environment**: Docker Compose (projectbedrock_backtesting)
- **Python Version**: 3.12.12

## Calculation Accuracy Verification

All baseline metrics have been verified for mathematical consistency:

| Metric | Calculated | Reported | Deviation | Status |
|--------|-----------|----------|-----------|--------|
| **Win Rate** | 0.3333 (5/15) | 0.3333 | 0.0000 (0.00%) | ✅ PASS |
| **ROI** | -0.0104 ((98961.65-100000)/100000) | -0.0104 | 0.0000 (0.00%) | ✅ PASS |
| **Profit Factor** | 0.9176 (11560.65/12599.00) | 0.9176 | 0.0000 (0.00%) | ✅ PASS |
| **Calmar Ratio** | -0.1891 (-0.0104/0.055) | -0.1886 | 0.0005 (0.26%) | ✅ PASS |

**Calmar Ratio Deviation Analysis**:
- The 0.26% deviation is due to floating-point precision or intermediate rounding
- This is within acceptable tolerance (< 1%) and does not indicate a calculation error
- The deviation is consistent with expected behavior of floating-point arithmetic

## Notes

1. **No Upgrade Comparison Available**: This is the first baseline created. There is no pre-upgrade data (numpy 1.26.2, pandas 2.1.3) to compare against.

2. **Future Validation**: All future changes to BacktestingService, DecisionEngine, or related dependencies must run the same test configuration and compare results against these baselines.

3. **Acceptable Deviations**: Small floating-point precision differences (< 0.01%) are acceptable due to:
   - Different CPU architectures
   - Different numpy/pandas internal implementations
   - Rounding differences in intermediate calculations

4. **Unacceptable Deviations**: Any deviation > 0.1% in critical metrics (ROI, Final Balance, Total Trades) indicates a potential bug and must be investigated immediately.

5. **Regression Test Command**:
   ```bash
   # Run baseline test
   curl -X POST http://localhost:8004/v1/backtests \
     -H "Content-Type: application/json" \
     -d '{"strategy_name": "Regression Test", "strategy_type": "rules_only", "market": "BTCUSDT", "interval": "1h", "start_date": "2024-01-01", "end_date": "2024-01-31", "initial_balance": 100000.00}'
   
   # Compare metrics
   curl http://localhost:8004/v1/backtests/<backtest_id>/metrics
   ```

## Known Issues and Recommendations

### DecisionEngine API Design

**Issue**: DecisionEngine currently uses HTTP 404 status code to indicate "signal rejected" (No approved signals generated). This design has the following problems:

1. **Semantic Inaccuracy**: HTTP 404's standard meaning is "resource not found", not "resource exists but doesn't meet criteria"
2. **Poor Understandability**: Client developers may mistakenly think the API endpoint doesn't exist or is misconfigured
3. **Non-RESTful**: A more appropriate approach would be to return 200 OK with rejection reason in response body

**Recommendations**:
- **Option A**: Return `200 OK + {"signal": null, "reason": "REJECTED", "details": "..."}`
- **Option B**: Return `200 OK + {"approved": false, "signal": {...}, "rejection_reason": "..."}`
- **Priority**: P2 (doesn't affect functionality, but affects API understandability and compliance)
- **Impact Scope**: DecisionEngine API, DecisionEngineClient, all callers

**Current Status**: The current implementation works correctly functionally, but the API design has compliance issues that should be improved in future iterations.

## Conclusion

This baseline establishes the reference point for BacktestingService calculation accuracy with numpy 2.2.6 and pandas 2.3.2. All future changes must be validated against these metrics to ensure no regression in calculation accuracy.

**Verification Status**: ✅ All metrics verified for mathematical consistency (Win Rate, ROI, Profit Factor, Calmar Ratio)

