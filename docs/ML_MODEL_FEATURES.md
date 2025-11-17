# ML Model Features Documentation

## Overview

This document describes the technical indicator features used by the XGBoost ML model for trading signal confidence scoring in the DecisionEngine Service (Phase 2).

**Model Version**: v1  
**Model Type**: XGBoost Binary Classifier  
**Target**: Bullish (1) vs Bearish/Sideways (0)  
**Output**: Confidence score [0-100]

---

## Feature List

The model uses **13 technical indicator features** calculated from K-line (candlestick) data:

| # | Feature Name | Description | Indicator Type | Typical Range |
|---|--------------|-------------|----------------|---------------|
| 1 | `rsi_14` | Relative Strength Index (14 periods) | Momentum | 0-100 |
| 2 | `macd` | MACD line (12, 26, 9) | Trend | -∞ to +∞ |
| 3 | `macd_signal` | MACD signal line | Trend | -∞ to +∞ |
| 4 | `macd_hist` | MACD histogram (MACD - Signal) | Trend | -∞ to +∞ |
| 5 | `ma_20` | Simple Moving Average (20 periods) | Trend | Price range |
| 6 | `ma_50` | Simple Moving Average (50 periods) | Trend | Price range |
| 7 | `bb_upper` | Bollinger Band upper (20, 2) | Volatility | Price range |
| 8 | `bb_middle` | Bollinger Band middle (20) | Volatility | Price range |
| 9 | `bb_lower` | Bollinger Band lower (20, 2) | Volatility | Price range |
| 10 | `atr_14` | Average True Range (14 periods) | Volatility | 0 to +∞ |
| 11 | `volume` | Current volume | Volume | 0 to +∞ |
| 12 | `volume_ma_20` | Volume Moving Average (20 periods) | Volume | 0 to +∞ |
| 13 | `price_change_pct` | Price change percentage | Momentum | -100 to +100 |

---

## Feature Engineering Details

### 1. Momentum Indicators

#### RSI (Relative Strength Index)
- **Formula**: RSI = 100 - (100 / (1 + RS)), where RS = Average Gain / Average Loss
- **Period**: 14
- **Interpretation**:
  - RSI > 70: Overbought (potential bearish signal)
  - RSI < 30: Oversold (potential bullish signal)
  - RSI 40-60: Neutral zone

#### Price Change Percentage
- **Formula**: `(close[-1] - close[-2]) / close[-2] * 100`
- **Interpretation**:
  - Positive: Upward momentum
  - Negative: Downward momentum

### 2. Trend Indicators

#### MACD (Moving Average Convergence Divergence)
- **Parameters**: Fast=12, Slow=26, Signal=9
- **Components**:
  - `macd`: Fast EMA - Slow EMA
  - `macd_signal`: 9-period EMA of MACD
  - `macd_hist`: MACD - Signal (histogram)
- **Interpretation**:
  - MACD > Signal: Bullish crossover
  - MACD < Signal: Bearish crossover
  - Histogram increasing: Strengthening trend

#### Moving Averages (MA)
- **MA_20**: Short-term trend (20 periods)
- **MA_50**: Medium-term trend (50 periods)
- **Interpretation**:
  - Price > MA: Uptrend
  - MA_20 > MA_50: Golden cross (bullish)
  - MA_20 < MA_50: Death cross (bearish)

### 3. Volatility Indicators

#### Bollinger Bands
- **Parameters**: Period=20, StdDev=2
- **Components**:
  - `bb_upper`: Middle + 2 * StdDev
  - `bb_middle`: 20-period SMA
  - `bb_lower`: Middle - 2 * StdDev
- **Interpretation**:
  - Price near upper band: Overbought
  - Price near lower band: Oversold
  - Band width: Volatility measure

#### ATR (Average True Range)
- **Period**: 14
- **Interpretation**:
  - High ATR: High volatility
  - Low ATR: Low volatility
  - Used for stop-loss and position sizing

### 4. Volume Indicators

#### Volume and Volume MA
- **Volume**: Current period volume
- **Volume MA**: 20-period average volume
- **Interpretation**:
  - Volume > Volume MA: Strong participation
  - Volume < Volume MA: Weak participation
  - Volume confirms price trends

---

## Feature Importance (Estimated)

Based on XGBoost model training, the estimated feature importance ranking:

| Rank | Feature | Importance | Rationale |
|------|---------|------------|-----------|
| 1 | `macd_hist` | High | Strong trend signal |
| 2 | `rsi_14` | High | Momentum indicator |
| 3 | `price_change_pct` | High | Recent momentum |
| 4 | `ma_20` vs `ma_50` | Medium | Trend direction |
| 5 | `volume` / `volume_ma_20` | Medium | Volume confirmation |
| 6 | `bb_upper`, `bb_lower` | Medium | Overbought/oversold |
| 7 | `atr_14` | Low | Volatility context |

**Note**: Actual feature importance will be calculated after model training and saved in `model_metrics.json`.

---

## Data Requirements

### Minimum K-line Data
- **Minimum periods**: 50 (to calculate MA_50)
- **Recommended periods**: 100 (for stable indicators)
- **Interval**: 1h (hourly K-lines)

### Required K-line Fields
```python
{
    'open': float,      # Opening price
    'high': float,      # Highest price
    'low': float,       # Lowest price
    'close': float,     # Closing price
    'volume': float     # Trading volume
}
```

---

## Model Training Data

### Synthetic Data Generation
- **Generator**: `MarketDataGenerator` (services/decision_engine/scripts/data_generator.py)
- **Trend Types**:
  - **Bullish**: drift=+0.2%, volatility=1%, label=1
  - **Bearish**: drift=-0.2%, volatility=1%, label=0
  - **Sideways**: drift=0%, volatility=0.5%, label=0
- **Training Samples**: 2000 (70% train, 15% val, 15% test)
- **Lookback Periods**: 100 K-lines per sample

### Training Parameters
- **Model**: XGBoostClassifier
- **n_estimators**: 100
- **max_depth**: 5
- **learning_rate**: 0.1
- **random_state**: 42

---

## Model Performance Baseline

**Baseline Metrics** (to be updated after training):

| Metric | Target | Actual |
|--------|--------|--------|
| Accuracy | > 55% | TBD |
| Precision | > 50% | TBD |
| Recall | > 50% | TBD |
| F1 Score | > 50% | TBD |
| AUC-ROC | > 0.55 | TBD |

**Note**: Metrics will be saved in `services/decision_engine/models/model_metrics.json` after training.

---

## Model Version History

### v1 (2025-11-11)
- **Status**: Initial version
- **Training Data**: Synthetic data (2000 samples)
- **Features**: 13 technical indicators
- **Model**: XGBoost Binary Classifier
- **Purpose**: Phase 2 architecture validation
- **Deployment**: Docker volume mount

### Future Versions
- **v2**: Train on real historical data
- **v3**: Add more features (e.g., order book, funding rate)
- **v4**: Ensemble model (XGBoost + LightGBM)

---

## Usage Example

```python
from services.decision_engine.app.services.feature_engineer import FeatureEngineer
from services.decision_engine.app.adapters.xgboost_adapter import XGBoostAdapter

# 1. Calculate features from K-line data
klines = [...]  # List of 100 K-line dicts
features = FeatureEngineer.calculate_features(klines)

# 2. Load ML model
adapter = XGBoostAdapter(
    model_path="services/decision_engine/models/xgboost_signal_confidence_v1.pkl"
)

# 3. Get prediction
if adapter.is_loaded():
    ml_score = adapter.predict(features)  # Returns 0-100
    print(f"ML Confidence Score: {ml_score:.2f}")
```

---

## Integration with RuleEngine

The ML model is integrated into the signal generation workflow:

1. **RuleEngine** generates signal based on rule-based strategies
2. **FeatureEngineer** calculates 13 technical indicators from K-line data
3. **XGBoostAdapter** predicts confidence score [0-100]
4. **Signal.ml_confidence_score** is updated with ML prediction
5. Signal is saved to database and published to Redis

**Graceful Degradation**:
- If ML model fails to load: `ml_confidence_score = None`
- If feature calculation fails: `ml_confidence_score = None`
- Signal generation continues without ML enrichment

---

## References

- **pandas_ta Documentation**: https://github.com/twopirllc/pandas-ta
- **XGBoost Documentation**: https://xgboost.readthedocs.io/
- **Technical Analysis Indicators**: https://www.investopedia.com/technical-analysis-4689657

---

**Last Updated**: 2025-11-11  
**Author**: Project Bedrock Team  
**Phase**: Phase 2 - ML Engine Integration

