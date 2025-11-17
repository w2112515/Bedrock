"""
Feature Engineer - Calculate technical indicators for ML models.

This module provides feature engineering capabilities for converting
raw K-line data into technical indicator features suitable for ML models.

Uses pandas_ta library for technical indicator calculations.
"""

import pandas as pd
import pandas_ta as ta
from typing import Dict, List, Any
import structlog

logger = structlog.get_logger()


class FeatureEngineer:
    """
    Feature engineering service for calculating technical indicators.
    
    This class is stateless and uses static methods for easy reuse
    in both training scripts and production prediction flows.
    
    Design Principles:
    - Single Responsibility: Only feature calculation
    - Reusability: Static methods, no state
    - Robustness: Handles calculation failures gracefully
    """
    
    @staticmethod
    def calculate_features(klines: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate technical indicator features from K-line data.
        
        Args:
            klines: List of K-line dictionaries, each containing:
                   - open: Opening price
                   - high: Highest price
                   - low: Lowest price
                   - close: Closing price
                   - volume: Trading volume
                   Minimum 100 K-lines recommended for accurate indicators.
        
        Returns:
            Dictionary of feature name -> value pairs.
            Returns empty dict if calculation fails.
        
        Features calculated:
        1. RSI (14) - Relative Strength Index
        2. MACD (12, 26, 9) - Moving Average Convergence Divergence
        3. MA (20, 50) - Moving Averages
        4. Bollinger Bands (20, 2) - Volatility bands
        5. ATR (14) - Average True Range
        6. Volume indicators
        7. Price change percentage
        """
        try:
            # Validate input
            if not klines or len(klines) < 50:
                logger.warning(
                    "feature_calculation_insufficient_data",
                    num_klines=len(klines) if klines else 0,
                    message="Insufficient K-line data for feature calculation"
                )
                return {}
            
            # Convert to DataFrame
            df = pd.DataFrame(klines)
            
            # Ensure required columns exist
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = set(required_cols) - set(df.columns)
            if missing_cols:
                logger.error(
                    "feature_calculation_missing_columns",
                    missing=list(missing_cols),
                    message="Required columns missing from K-line data"
                )
                return {}
            
            # Initialize features dictionary
            features = {}
            
            # ============================================
            # 1. RSI (Relative Strength Index)
            # ============================================
            rsi = ta.rsi(df['close'], length=14)
            if rsi is not None and not rsi.empty and not pd.isna(rsi.iloc[-1]):
                features['rsi_14'] = float(rsi.iloc[-1])
            else:
                features['rsi_14'] = 50.0  # Neutral default
            
            # ============================================
            # 2. MACD (Moving Average Convergence Divergence)
            # ============================================
            macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
            if macd is not None and not macd.empty:
                features['macd'] = float(macd['MACD_12_26_9'].iloc[-1]) if not pd.isna(macd['MACD_12_26_9'].iloc[-1]) else 0.0
                features['macd_signal'] = float(macd['MACDs_12_26_9'].iloc[-1]) if not pd.isna(macd['MACDs_12_26_9'].iloc[-1]) else 0.0
                features['macd_hist'] = float(macd['MACDh_12_26_9'].iloc[-1]) if not pd.isna(macd['MACDh_12_26_9'].iloc[-1]) else 0.0
            else:
                features['macd'] = 0.0
                features['macd_signal'] = 0.0
                features['macd_hist'] = 0.0
            
            # ============================================
            # 3. Moving Averages
            # ============================================
            ma_20 = ta.sma(df['close'], length=20)
            ma_50 = ta.sma(df['close'], length=50)
            
            if ma_20 is not None and not ma_20.empty and not pd.isna(ma_20.iloc[-1]):
                features['ma_20'] = float(ma_20.iloc[-1])
            else:
                features['ma_20'] = float(df['close'].iloc[-1])
            
            if ma_50 is not None and not ma_50.empty and not pd.isna(ma_50.iloc[-1]):
                features['ma_50'] = float(ma_50.iloc[-1])
            else:
                features['ma_50'] = float(df['close'].iloc[-1])
            
            # ============================================
            # 4. Bollinger Bands
            # ============================================
            bbands = ta.bbands(df['close'], length=20, std=2)
            if bbands is not None and not bbands.empty:
                # pandas_ta column names vary by version, find them dynamically
                bb_cols = bbands.columns.tolist()
                # Find upper, middle, lower columns
                upper_col = [c for c in bb_cols if 'BBU' in c or 'upper' in c.lower()]
                middle_col = [c for c in bb_cols if 'BBM' in c or 'middle' in c.lower()]
                lower_col = [c for c in bb_cols if 'BBL' in c or 'lower' in c.lower()]

                if upper_col and middle_col and lower_col:
                    features['bb_upper'] = float(bbands[upper_col[0]].iloc[-1]) if not pd.isna(bbands[upper_col[0]].iloc[-1]) else float(df['close'].iloc[-1])
                    features['bb_middle'] = float(bbands[middle_col[0]].iloc[-1]) if not pd.isna(bbands[middle_col[0]].iloc[-1]) else float(df['close'].iloc[-1])
                    features['bb_lower'] = float(bbands[lower_col[0]].iloc[-1]) if not pd.isna(bbands[lower_col[0]].iloc[-1]) else float(df['close'].iloc[-1])
                else:
                    current_close = float(df['close'].iloc[-1])
                    features['bb_upper'] = current_close
                    features['bb_middle'] = current_close
                    features['bb_lower'] = current_close
            else:
                current_close = float(df['close'].iloc[-1])
                features['bb_upper'] = current_close
                features['bb_middle'] = current_close
                features['bb_lower'] = current_close
            
            # ============================================
            # 5. ATR (Average True Range)
            # ============================================
            atr = ta.atr(df['high'], df['low'], df['close'], length=14)
            if atr is not None and not atr.empty and not pd.isna(atr.iloc[-1]):
                features['atr_14'] = float(atr.iloc[-1])
            else:
                features['atr_14'] = 0.0
            
            # ============================================
            # 6. Volume Indicators
            # ============================================
            features['volume'] = float(df['volume'].iloc[-1])
            volume_ma = df['volume'].rolling(window=20).mean()
            if not volume_ma.empty and not pd.isna(volume_ma.iloc[-1]):
                features['volume_ma_20'] = float(volume_ma.iloc[-1])
            else:
                features['volume_ma_20'] = float(df['volume'].iloc[-1])
            
            # ============================================
            # 7. Price Change Percentage
            # ============================================
            if len(df) >= 2:
                price_change = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100
                features['price_change_pct'] = float(price_change)
            else:
                features['price_change_pct'] = 0.0
            
            # Log success
            logger.debug(
                "feature_calculation_success",
                num_features=len(features),
                features=list(features.keys())
            )
            
            return features
        
        except Exception as e:
            logger.error(
                "feature_calculation_failed",
                error=str(e),
                num_klines=len(klines) if klines else 0,
                message="Feature calculation failed. Returning empty dict."
            )
            return {}
    
    @staticmethod
    def get_feature_names() -> List[str]:
        """
        Get list of all feature names in the correct order.
        
        Returns:
            List of feature names
        """
        return [
            'rsi_14',
            'macd',
            'macd_signal',
            'macd_hist',
            'ma_20',
            'ma_50',
            'bb_upper',
            'bb_middle',
            'bb_lower',
            'atr_14',
            'volume',
            'volume_ma_20',
            'price_change_pct'
        ]

    @staticmethod
    def calculate_features_multifreq(
        primary_klines: List[Dict[str, Any]],
        secondary_klines: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Calculate technical indicator features from multiple time frequencies.

        Args:
            primary_klines: Primary interval K-lines (e.g., 1h, 100 K-lines)
            secondary_klines: Secondary interval K-lines (e.g., 4h, ~25 K-lines)

        Returns:
            Dictionary of feature name -> value pairs.
            Includes all primary features + secondary frequency features.
        """
        # Calculate primary features (1h)
        features = FeatureEngineer.calculate_features(primary_klines)

        if not features:
            return {}

        # Calculate secondary features (4h)
        try:
            if not secondary_klines or len(secondary_klines) < 20:
                logger.warning(
                    "insufficient_secondary_klines",
                    num_klines=len(secondary_klines) if secondary_klines else 0
                )
                # Return primary features only
                return features

            # Convert to DataFrame
            df_4h = pd.DataFrame(secondary_klines)

            # RSI (14) on 4h
            rsi_4h = ta.rsi(df_4h['close'], length=14)
            if rsi_4h is not None and not rsi_4h.empty and not pd.isna(rsi_4h.iloc[-1]):
                features['rsi_14_4h'] = float(rsi_4h.iloc[-1])
            else:
                features['rsi_14_4h'] = 50.0

            # MACD on 4h
            macd_4h = ta.macd(df_4h['close'], fast=12, slow=26, signal=9)
            if macd_4h is not None and not macd_4h.empty:
                features['macd_4h'] = float(macd_4h['MACD_12_26_9'].iloc[-1]) if not pd.isna(macd_4h['MACD_12_26_9'].iloc[-1]) else 0.0
                features['macd_signal_4h'] = float(macd_4h['MACDs_12_26_9'].iloc[-1]) if not pd.isna(macd_4h['MACDs_12_26_9'].iloc[-1]) else 0.0
            else:
                features['macd_4h'] = 0.0
                features['macd_signal_4h'] = 0.0

            # MA (20) on 4h
            ma_20_4h = ta.sma(df_4h['close'], length=20)
            if ma_20_4h is not None and not ma_20_4h.empty and not pd.isna(ma_20_4h.iloc[-1]):
                features['ma_20_4h'] = float(ma_20_4h.iloc[-1])
            else:
                features['ma_20_4h'] = float(df_4h['close'].iloc[-1])

            # Volume MA (20) on 4h
            volume_ma_20_4h = ta.sma(df_4h['volume'], length=20)
            if volume_ma_20_4h is not None and not volume_ma_20_4h.empty and not pd.isna(volume_ma_20_4h.iloc[-1]):
                features['volume_ma_20_4h'] = float(volume_ma_20_4h.iloc[-1])
            else:
                features['volume_ma_20_4h'] = float(df_4h['volume'].iloc[-1])

            # ATR (14) on 4h
            atr_4h = ta.atr(df_4h['high'], df_4h['low'], df_4h['close'], length=14)
            if atr_4h is not None and not atr_4h.empty and not pd.isna(atr_4h.iloc[-1]):
                features['atr_14_4h'] = float(atr_4h.iloc[-1])
            else:
                features['atr_14_4h'] = 0.0

            logger.debug(
                "multifreq_features_calculated",
                primary_features=13,
                secondary_features=6,
                total_features=len(features)
            )

        except Exception as e:
            logger.error(
                "secondary_feature_calculation_failed",
                error=str(e),
                message="Returning primary features only"
            )

        return features

    @staticmethod
    def get_feature_names_multifreq() -> List[str]:
        """
        Get list of all feature names for multi-frequency features.

        Returns:
            List of feature names (primary + secondary)
        """
        primary_features = FeatureEngineer.get_feature_names()
        secondary_features = [
            'rsi_14_4h',
            'macd_4h',
            'macd_signal_4h',
            'ma_20_4h',
            'volume_ma_20_4h',
            'atr_14_4h'
        ]
        return primary_features + secondary_features

    @staticmethod
    def calculate_features_crosspair(
        primary_klines: List[Dict[str, Any]],
        secondary_klines: List[Dict[str, Any]],
        reference_klines: Dict[str, List[Dict[str, Any]]],
        target_symbol: str
    ) -> Dict[str, float]:
        """
        Calculate technical indicator features with cross-pair features (v2.7 model).

        降级策略（Degradation Strategy）：
        - 如果某个参考币种的K线数据为空列表或数据不足，对应的跨币种特征值设为0.0（中性值）
        - 这确保即使部分参考币种数据缺失，模型仍然可以正常预测
        - 调用方应在日志中记录缺失的参考币种，便于监控和排查问题

        Args:
            primary_klines: Primary interval K-lines (e.g., 1h, 100 K-lines)
            secondary_klines: Secondary interval K-lines (e.g., 4h, ~25 K-lines)
            reference_klines: Reference symbol K-lines dict {symbol: [klines]}
                             可以包含空列表，表示该币种数据缺失
            target_symbol: Target symbol (to exclude self-reference)

        Returns:
            Dictionary of feature name -> value pairs.
            Includes 19 multi-freq features + 11 cross-pair features = 30 total.

            如果参考币种数据缺失，对应特征值为0.0（中性值）：
            - BTC数据缺失：btc_return_*、btc_trend_4h = 0.0
            - ETH数据缺失：eth_return_* = 0.0
            - 多个币种缺失：market_return_1h、market_bullish_ratio 使用可用数据计算
            - 所有币种缺失：所有跨币种特征 = 0.0
        """
        # Calculate base multi-frequency features (19 features)
        features = FeatureEngineer.calculate_features_multifreq(primary_klines, secondary_klines)

        if not features:
            return {}

        # Calculate cross-pair features (11 features)
        try:
            # Extract reference symbols data
            # 注意：reference_klines中的值可能是空列表（表示数据缺失）
            # 降级策略：空列表会导致 len() 检查失败，从而使用中性值0.0
            btc_klines = reference_klines.get('BTCUSDT', [])
            eth_klines = reference_klines.get('ETHUSDT', [])
            bnb_klines = reference_klines.get('BNBUSDT', [])
            sol_klines = reference_klines.get('SOLUSDT', [])
            ada_klines = reference_klines.get('ADAUSDT', [])

            # ============================================
            # 1. BTC Leading Indicators (5 features)
            # ============================================
            # 降级策略：如果BTC数据缺失（空列表）或数据不足，使用中性值0.0
            if target_symbol != 'BTCUSDT' and len(btc_klines) >= 25:
                # btc_return_1h_lag: BTC 1h return at t-1
                btc_close_t1 = btc_klines[-1]['close']
                btc_close_t2 = btc_klines[-2]['close']
                features['btc_return_1h_lag'] = (btc_close_t1 - btc_close_t2) / btc_close_t2

                # btc_return_2h_lag: BTC 2h return at t-1
                btc_close_t3 = btc_klines[-3]['close']
                features['btc_return_2h_lag'] = (btc_close_t1 - btc_close_t3) / btc_close_t3

                # btc_return_4h_lag: BTC 4h return at t-1
                btc_close_t5 = btc_klines[-5]['close']
                features['btc_return_4h_lag'] = (btc_close_t1 - btc_close_t5) / btc_close_t5

                # btc_return_24h_lag: BTC 24h return at t-1
                btc_close_t25 = btc_klines[-25]['close']
                features['btc_return_24h_lag'] = (btc_close_t1 - btc_close_t25) / btc_close_t25

                # btc_trend_4h: BTC trend indicator (1 if above MA20, else 0)
                btc_df = pd.DataFrame(btc_klines[-20:])
                btc_ma20 = btc_df['close'].mean()
                features['btc_trend_4h'] = 1.0 if btc_close_t1 > btc_ma20 else 0.0
            else:
                # Target is BTC or insufficient data (降级：使用中性值0.0)
                features['btc_return_1h_lag'] = 0.0
                features['btc_return_2h_lag'] = 0.0
                features['btc_return_4h_lag'] = 0.0
                features['btc_return_24h_lag'] = 0.0
                features['btc_trend_4h'] = 0.0

            # ============================================
            # 2. ETH Leading Indicators (2 features)
            # ============================================
            # 降级策略：如果ETH数据缺失（空列表）或数据不足，使用中性值0.0
            if target_symbol != 'ETHUSDT' and len(eth_klines) >= 3:
                # eth_return_1h_lag: ETH 1h return at t-1
                eth_close_t1 = eth_klines[-1]['close']
                eth_close_t2 = eth_klines[-2]['close']
                features['eth_return_1h_lag'] = (eth_close_t1 - eth_close_t2) / eth_close_t2

                # eth_return_2h_lag: ETH 2h return at t-1
                eth_close_t3 = eth_klines[-3]['close']
                features['eth_return_2h_lag'] = (eth_close_t1 - eth_close_t3) / eth_close_t3
            else:
                # Target is ETH or insufficient data (降级：使用中性值0.0)
                features['eth_return_1h_lag'] = 0.0
                features['eth_return_2h_lag'] = 0.0

            # ============================================
            # 3. Market Overall Trend (2 features)
            # ============================================
            # 降级策略：只使用有数据的币种计算市场整体趋势
            # 如果少于3个币种有数据，使用中性值
            # Collect all 5 coins' 1h returns at t-1
            all_returns = []
            for ref_klines in [btc_klines, eth_klines, bnb_klines, sol_klines, ada_klines]:
                if len(ref_klines) >= 2:
                    close_t1 = ref_klines[-1]['close']
                    close_t2 = ref_klines[-2]['close']
                    ret = (close_t1 - close_t2) / close_t2
                    all_returns.append(ret)

            if len(all_returns) >= 3:
                # market_return_1h: Average return across all coins
                features['market_return_1h'] = sum(all_returns) / len(all_returns)

                # market_bullish_ratio: Proportion of coins with positive return
                bullish_count = sum(1 for r in all_returns if r > 0)
                features['market_bullish_ratio'] = bullish_count / len(all_returns)
            else:
                # 降级：少于3个币种有数据，使用中性值
                features['market_return_1h'] = 0.0
                features['market_bullish_ratio'] = 0.5  # 50%中性值

            # ============================================
            # 4. Inter-Coin Correlation (2 features)
            # ============================================
            # btc_eth_corr_24h: Correlation between BTC and ETH returns over 24h
            if len(btc_klines) >= 25 and len(eth_klines) >= 25:
                btc_returns_24h = []
                eth_returns_24h = []
                for i in range(-24, 0):
                    btc_ret = (btc_klines[i]['close'] - btc_klines[i-1]['close']) / btc_klines[i-1]['close']
                    eth_ret = (eth_klines[i]['close'] - eth_klines[i-1]['close']) / eth_klines[i-1]['close']
                    btc_returns_24h.append(btc_ret)
                    eth_returns_24h.append(eth_ret)

                features['btc_eth_corr_24h'] = FeatureEngineer._calculate_correlation(
                    btc_returns_24h, eth_returns_24h
                )
            else:
                features['btc_eth_corr_24h'] = 0.0

            # btc_target_corr_24h: Correlation between BTC and target coin returns over 24h
            if target_symbol != 'BTCUSDT' and len(btc_klines) >= 25 and len(primary_klines) >= 25:
                btc_returns_24h = []
                target_returns_24h = []
                for i in range(-24, 0):
                    btc_ret = (btc_klines[i]['close'] - btc_klines[i-1]['close']) / btc_klines[i-1]['close']
                    target_ret = (primary_klines[i]['close'] - primary_klines[i-1]['close']) / primary_klines[i-1]['close']
                    btc_returns_24h.append(btc_ret)
                    target_returns_24h.append(target_ret)

                features['btc_target_corr_24h'] = FeatureEngineer._calculate_correlation(
                    btc_returns_24h, target_returns_24h
                )
            else:
                features['btc_target_corr_24h'] = 0.0

            logger.debug(
                "crosspair_feature_calculation_success",
                num_features=len(features),
                target_symbol=target_symbol
            )

        except Exception as e:
            logger.error(
                "crosspair_feature_calculation_failed",
                error=str(e),
                target_symbol=target_symbol,
                message="Returning multi-freq features only"
            )

        return features

    @staticmethod
    def _calculate_correlation(x: List[float], y: List[float]) -> float:
        """
        Calculate Pearson correlation coefficient between two lists.

        Args:
            x: First list of values
            y: Second list of values

        Returns:
            Correlation coefficient (-1 to 1), or 0.0 if calculation fails
        """
        try:
            if len(x) != len(y) or len(x) < 2:
                return 0.0

            # Calculate means
            mean_x = sum(x) / len(x)
            mean_y = sum(y) / len(y)

            # Calculate covariance and standard deviations
            cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(len(x)))
            std_x = (sum((xi - mean_x) ** 2 for xi in x)) ** 0.5
            std_y = (sum((yi - mean_y) ** 2 for yi in y)) ** 0.5

            # Avoid division by zero
            if std_x == 0 or std_y == 0:
                return 0.0

            return cov / (std_x * std_y)

        except Exception:
            return 0.0

    @staticmethod
    def get_feature_names_crosspair() -> List[str]:
        """
        Get list of all feature names for cross-pair features.

        Returns:
            List of feature names (19 multi-freq + 11 cross-pair = 30 total)
        """
        multifreq_features = FeatureEngineer.get_feature_names_multifreq()
        crosspair_features = [
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
        return multifreq_features + crosspair_features

