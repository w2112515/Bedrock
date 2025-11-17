"""
Rule Engine

Integrates all strategies to generate trading signals.
Orchestrates the signal generation workflow.

Phase 2: Integrated with ML engine for confidence scoring.
Phase 2.7: Support for v2.7 model with cross-pair features.
"""

import sys
import os
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import httpx
import asyncio

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from services.decision_engine.app.core.config import settings, MLModelVersion
from services.decision_engine.app.models.signal import Signal, FundingRateSignal
from services.decision_engine.app.strategies.market_filter import MarketFilter
from services.decision_engine.app.strategies.pullback_entry import PullbackEntryStrategy
from services.decision_engine.app.strategies.exit_strategy import ExitStrategy
from services.decision_engine.app.strategies.funding_rate_strategy import FundingRateStrategy
from services.decision_engine.app.adapters.ml_model_interface import MLModelInterface
from services.decision_engine.app.adapters.llm_interface import LLMInterface
from services.decision_engine.app.services.feature_engineer import FeatureEngineer
from services.decision_engine.app.engines.arbiter import DecisionArbiter, ArbitrationConfigError
from services.decision_engine.app.events.publisher import EventPublisher

logger = setup_logging("rule_engine")


class RuleEngine:
    """
    Rule engine for signal generation.

    Workflow:
    1. MarketFilter filters markets based on trend and onchain data
    2. PullbackEntryStrategy analyzes entry signals
    3. ExitStrategy calculates exit prices
    4. Create Signal objects and save to database
    5. (Phase 2) Enrich signals with ML confidence scores

    Phase 1: Rule engine only
    Phase 2: Integrated with ML and LLM engines
    """

    def __init__(
        self,
        ml_adapter: Optional[MLModelInterface] = None,
        llm_adapter: Optional[LLMInterface] = None,
        event_publisher: Optional[EventPublisher] = None
    ):
        """
        Initialize RuleEngine.

        Args:
            ml_adapter: Optional ML model adapter for confidence scoring (Phase 2)
            llm_adapter: Optional LLM adapter for sentiment analysis (Phase 2)
            event_publisher: Optional event publisher for signal events (Phase 2)
        """
        self.market_filter = MarketFilter()
        self.pullback_strategy = PullbackEntryStrategy()
        self.exit_strategy = ExitStrategy()
        self.ml_adapter = ml_adapter
        self.llm_adapter = llm_adapter
        self.feature_engineer = FeatureEngineer()
        self.arbiter = DecisionArbiter()
        self.event_publisher = event_publisher

        # Initialize funding rate strategy (Phase 2)
        self.funding_rate_strategy = None
        if settings.FUNDING_RATE_ENABLED:
            self.funding_rate_strategy = FundingRateStrategy()
            logger.info("Funding rate strategy enabled")
        
    async def analyze(
        self, 
        symbols: List[str],
        db: Session,
        interval: str = "1h"
    ) -> List[Signal]:
        """
        Analyze markets and generate signals.
        
        Args:
            symbols: List of trading symbols
            db: Database session
            interval: K-line interval (default: "1h")
            
        Returns:
            List of generated Signal objects
        """
        logger.info(f"Starting signal analysis for {len(symbols)} symbols")
        
        signals = []
        
        try:
            # 1. Filter markets
            filtered_markets = await self.market_filter.filter_markets(
                symbols=symbols,
                interval=interval,
                limit=100
            )
            
            if not filtered_markets:
                logger.info("No markets passed filter criteria")
                return signals
            
            logger.info(f"{len(filtered_markets)} markets passed filter")
            
            # 2. Analyze each filtered market
            for market in filtered_markets:
                try:
                    signal = await self._analyze_market(market, db)
                    if signal:
                        signals.append(signal)
                        logger.info(f"Generated signal for {market['symbol']}: {signal.id}")
                        
                except Exception as e:
                    logger.error(f"Error analyzing market {market['symbol']}: {e}")
                    continue
            
            logger.info(f"Generated {len(signals)} signals from {len(filtered_markets)} markets")
            
        except Exception as e:
            logger.error(f"Error in rule engine analysis: {e}")
        
        return signals
    
    async def _analyze_market(
        self, 
        market_data: dict,
        db: Session
    ) -> Optional[Signal]:
        """
        Analyze a single market and create signal.
        
        Args:
            market_data: Market data from MarketFilter
            db: Database session
            
        Returns:
            Signal object or None
        """
        try:
            symbol = market_data["symbol"]

            logger.info(f"[DEBUG] Starting _analyze_market for {symbol}")

            # 1. Analyze entry signal
            entry_signal = self.pullback_strategy.analyze(market_data)
            if not entry_signal:
                logger.debug(f"No entry signal for {symbol}")
                return None

            logger.info(f"[DEBUG] Entry signal for {symbol}: score={entry_signal.get('rule_engine_score')}")

            # Check minimum score threshold
            if entry_signal["rule_engine_score"] < settings.MIN_RULE_ENGINE_SCORE:
                logger.info(
                    f"Signal for {symbol} below minimum score: "
                    f"{entry_signal['rule_engine_score']} < {settings.MIN_RULE_ENGINE_SCORE}"
                )
                return None
            
            # 2. Calculate exit prices (already done in PullbackEntryStrategy)
            # ExitStrategy is available for future use or manual calculations
            
            # 3. Create Signal object
            signal = Signal(
                market=symbol,
                signal_type=entry_signal["signal_type"],
                entry_price=entry_signal["entry_price"],
                stop_loss_price=entry_signal["stop_loss_price"],
                profit_target_price=entry_signal["profit_target_price"],
                risk_unit_r=entry_signal["risk_unit_r"],
                suggested_position_weight=entry_signal["suggested_position_weight"],
                reward_risk_ratio=entry_signal["reward_risk_ratio"],
                onchain_signals=market_data.get("onchain_data"),
                rule_engine_score=entry_signal["rule_engine_score"],
                # Phase 2 fields (will be enriched by ML)
                ml_confidence_score=None,
                llm_sentiment=None,
                final_decision=None,
                explanation=None
            )

            # 4. (Phase 2) Enrich signal with ML confidence score
            # 转换K线字段名（DataHub格式 -> FeatureEngineer格式）
            klines_normalized = self._normalize_kline_fields(market_data.get("kline_data", []))
            signal = await self._enrich_with_ml_score(signal, klines_normalized)

            # 5. (Phase 2) Enrich signal with LLM sentiment analysis
            signal = await self._enrich_with_llm_sentiment(signal, klines_normalized)

            # 6. (Phase 2) Enrich signal with funding rate signal
            if settings.FUNDING_RATE_ENABLED and self.funding_rate_strategy:
                signal = await self._enrich_with_funding_rate(signal, symbol)

            # 7. (Phase 2) Arbitrate final decision
            signal = await self._arbitrate_decision(signal, db)

            # 8. Save to database
            db.add(signal)
            db.commit()
            db.refresh(signal)

            logger.info(
                f"Created signal {signal.id} for {symbol}: "
                f"entry={signal.entry_price}, score={signal.rule_engine_score}, "
                f"weight={signal.suggested_position_weight}, "
                f"decision={signal.final_decision}"
            )

            # 8. (Phase 2) Publish signal event
            if self.event_publisher:
                try:
                    # Determine channel based on final_decision
                    channel = "signal.created" if signal.final_decision == "APPROVED" else "signal.rejected"

                    logger.info(
                        f"Publishing signal event: signal_id={signal.id}, "
                        f"market={symbol}, decision={signal.final_decision}, "
                        f"channel={channel}"
                    )

                    success = await self.event_publisher.publish_signal_created(signal)

                    if success:
                        logger.info(
                            f"Signal event published successfully: "
                            f"signal_id={signal.id}, channel={channel}"
                        )
                    else:
                        logger.error(
                            f"Failed to publish signal event: "
                            f"signal_id={signal.id}, channel={channel}"
                        )
                except Exception as e:
                    logger.error(
                        f"Error publishing signal event for {signal.id}: {e}",
                        exc_info=True
                    )

            return signal
            
        except Exception as e:
            logger.error(f"Error creating signal for {market_data.get('symbol')}: {e}")
            db.rollback()
            return None
    
    async def analyze_single_market(
        self,
        symbol: str,
        db: Session,
        interval: str = "1h"
    ) -> Optional[Signal]:
        """
        Analyze a single market and generate signal.
        
        Convenience method for manual signal generation.
        
        Args:
            symbol: Trading symbol
            db: Database session
            interval: K-line interval
            
        Returns:
            Signal object or None
        """
        logger.info(f"Analyzing single market: {symbol}")
        
        try:
            # Filter single market
            filtered_markets = await self.market_filter.filter_markets(
                symbols=[symbol],
                interval=interval,
                limit=100
            )
            
            if not filtered_markets:
                logger.info(f"Market {symbol} did not pass filter")
                return None
            
            # Analyze market
            signal = await self._analyze_market(filtered_markets[0], db)
            return signal
            
        except Exception as e:
            logger.error(f"Error analyzing single market {symbol}: {e}")
            return None

    async def _enrich_with_ml_score(
        self,
        signal: Signal,
        klines: List[Dict[str, Any]]
    ) -> Signal:
        """
        Enrich signal with ML confidence score (Phase 2 - Task 2.1.10).

        支持多版本模型（v1/v2_6/v2_7）：
        - v1: 使用 calculate_features() 计算13个基础特征
        - v2_6: 使用 calculate_features_multifreq() 计算19个多频特征
        - v2_7: 使用 calculate_features_crosspair() 计算30个特征（需要额外数据）

        This method:
        1. Checks if ML adapter is available
        2. Determines model version and selects appropriate feature calculation method
        3. For v2.7: Fetches additional data (4h klines + reference symbols)
        4. Calculates features based on model version
        5. Calls ML model for prediction
        6. Updates signal.ml_confidence_score

        Args:
            signal: Signal object to enrich
            klines: K-line data (1h) for feature calculation

        Returns:
            Enriched signal object (ml_confidence_score may be None if ML unavailable)
        """
        # Check if ML adapter is available
        if not self.ml_adapter:
            logger.debug(
                "ml_enrichment_skipped",
                reason="ml_adapter_not_configured",
                signal_id=str(signal.id)
            )
            return signal

        if not self.ml_adapter.is_loaded():
            logger.debug(
                "ml_enrichment_skipped",
                reason="ml_model_not_loaded",
                signal_id=str(signal.id)
            )
            return signal

        try:
            # 根据模型版本选择特征计算方法
            model_version = settings.ML_MODEL_VERSION

            if model_version == MLModelVersion.V2_7.value:
                # v2.7模型：需要额外获取4h K线和参考币种K线
                logger.debug(f"Using v2.7 feature calculation for {signal.market}")

                # 获取额外数据（4h K线 + 参考币种K线）
                additional_data = await self._get_multifreq_and_reference_klines(
                    symbol=signal.market,
                    primary_klines=klines
                )

                if not additional_data:
                    logger.warning(
                        "ml_enrichment_failed",
                        reason="failed_to_fetch_additional_data_for_v2_7",
                        signal_id=str(signal.id),
                        market=signal.market
                    )
                    return signal

                # 计算v2.7特征（30个特征）
                features = self.feature_engineer.calculate_features_crosspair(
                    primary_klines=klines,
                    secondary_klines=additional_data["secondary_klines"],
                    reference_klines=additional_data["reference_klines"],
                    target_symbol=signal.market
                )

                # 记录缺失的参考币种（如果有）
                missing_symbols = additional_data.get("missing_reference_symbols", [])
                if missing_symbols:
                    logger.warning(
                        "v2_7_reference_symbols_missing",
                        missing_symbols=missing_symbols,
                        signal_id=str(signal.id),
                        market=signal.market,
                        message="Some reference symbols data missing, using neutral values (0.0) for cross-pair features"
                    )

            elif model_version == MLModelVersion.V2_6.value:
                # v2.6模型：需要1h和4h K线
                logger.debug(f"Using v2.6 feature calculation for {signal.market}")

                # 获取4h K线
                secondary_klines = await self._get_secondary_klines(signal.market, "4h", 25)

                if not secondary_klines:
                    logger.warning(
                        "ml_enrichment_failed",
                        reason="failed_to_fetch_4h_klines_for_v2_6",
                        signal_id=str(signal.id),
                        market=signal.market
                    )
                    return signal

                # 计算v2.6特征（19个特征）
                features = self.feature_engineer.calculate_features_multifreq(
                    primary_klines=klines,
                    secondary_klines=secondary_klines
                )

            else:
                # v1模型：只需要1h K线
                logger.debug(f"Using v1 feature calculation for {signal.market}")
                features = self.feature_engineer.calculate_features(klines)

            if not features:
                logger.warning(
                    "ml_enrichment_failed",
                    reason="feature_calculation_failed",
                    signal_id=str(signal.id),
                    market=signal.market,
                    model_version=model_version
                )
                return signal

            # Call ML model for prediction
            ml_score = self.ml_adapter.predict(features)

            if ml_score is not None:
                signal.ml_confidence_score = ml_score
                logger.info(
                    "ml_enrichment_success",
                    signal_id=str(signal.id),
                    market=signal.market,
                    model_version=model_version,
                    ml_score=f"{ml_score:.2f}",
                    rule_score=f"{signal.rule_engine_score:.2f}",
                    num_features=len(features)
                )
            else:
                logger.warning(
                    "ml_enrichment_failed",
                    reason="ml_prediction_returned_none",
                    signal_id=str(signal.id),
                    market=signal.market,
                    model_version=model_version
                )

        except Exception as e:
            logger.error(
                "ml_enrichment_error",
                error=str(e),
                signal_id=str(signal.id),
                market=signal.market,
                model_version=settings.ML_MODEL_VERSION
            )

        return signal

    async def _enrich_with_llm_sentiment(
        self,
        signal: Signal,
        klines: List[Dict[str, Any]]
    ) -> Signal:
        """
        Enrich signal with LLM sentiment analysis (Phase 2 - Task 2.2.10).

        This method:
        1. Checks if LLM adapter is available
        2. Prepares input data (market data, technical indicators, signal details)
        3. Calls LLM adapter for sentiment analysis
        4. Updates signal.llm_sentiment and signal.explanation

        Args:
            signal: Signal object to enrich
            klines: K-line data for feature calculation

        Returns:
            Enriched signal object (llm_sentiment may be None if LLM unavailable)
        """
        # Check if LLM adapter is available
        if not self.llm_adapter or not self.llm_adapter.is_available():
            logger.info(
                "llm_adapter_unavailable",
                signal_id=str(signal.id),
                market=signal.market
            )
            return signal

        try:
            # Prepare technical indicators
            features = self.feature_engineer.calculate_features(klines)

            # Prepare market data
            latest_kline = klines[-1]
            current_price = float(latest_kline["close"])

            # Calculate 24h price change
            if len(klines) >= 24:
                price_24h_ago = float(klines[-24]["close"])
                price_change_24h = (current_price - price_24h_ago) / price_24h_ago * 100
            else:
                price_change_24h = 0.0

            volume_24h = sum(float(k["volume"]) for k in klines[-24:])

            # Call LLM for sentiment analysis
            logger.info(
                "calling_llm_sentiment_analysis",
                signal_id=str(signal.id),
                market=signal.market
            )

            result = await self.llm_adapter.analyze_sentiment(
                market=signal.market,
                current_price=current_price,
                price_change_24h=price_change_24h,
                volume_24h=volume_24h,
                technical_indicators=features,
                signal_type=signal.signal_type,
                entry_price=float(signal.entry_price),
                stop_loss_price=float(signal.stop_loss_price),
                profit_target_price=float(signal.profit_target_price),
                rule_engine_score=signal.rule_engine_score,
                ml_confidence_score=signal.ml_confidence_score
            )

            # Update Signal
            if result:
                signal.llm_sentiment = result["sentiment"]
                signal.explanation = result["explanation"]
                logger.info(
                    "llm_sentiment_success",
                    signal_id=str(signal.id),
                    market=signal.market,
                    sentiment=result["sentiment"],
                    confidence=f"{result['confidence']:.2f}"
                )
            else:
                logger.warning(
                    "llm_sentiment_failed",
                    reason="llm_returned_none",
                    signal_id=str(signal.id),
                    market=signal.market
                )

        except Exception as e:
            logger.error(
                "llm_sentiment_error",
                error=str(e),
                signal_id=str(signal.id),
                market=signal.market
            )

        return signal

    async def _arbitrate_decision(
        self,
        signal: Signal,
        db: Session
    ) -> Signal:
        """
        Arbitrate final decision based on all scores (Phase 2 - Task 2.3.6).

        This method:
        1. Calls DecisionArbiter to combine all scores
        2. Updates signal.final_decision, signal.explanation, signal.rejection_reason
        3. Returns enriched signal object

        Args:
            signal: Signal object with all scores populated
            db: Database session

        Returns:
            Enriched signal object with final_decision set
        """
        try:
            # Call arbiter to make final decision
            final_decision, explanation, rejection_reason = await self.arbiter.arbitrate(
                signal=signal,
                db=db
            )

            # Update signal
            signal.final_decision = final_decision
            signal.explanation = explanation
            signal.rejection_reason = rejection_reason

            logger.info(
                "arbitration_complete",
                signal_id=str(signal.id),
                market=signal.market,
                final_decision=final_decision,
                rule_score=signal.rule_engine_score,
                ml_score=signal.ml_confidence_score,
                llm_sentiment=signal.llm_sentiment
            )

        except Exception as e:
            # Classify arbitration errors to distinguish configuration vs system failures
            if isinstance(e, ArbitrationConfigError):
                error_category = "CONFIG_ERROR"
            elif isinstance(e, SQLAlchemyError):
                error_category = "SYSTEM_ERROR"
            else:
                error_category = "SYSTEM_ERROR"

            logger.exception(
                "arbitration_error",
                error=str(e),
                error_category=error_category,
                signal_id=str(signal.id),
                market=signal.market
            )
            # Fallback: Set to REJECTED on error (safety first)
            signal.final_decision = "REJECTED"
            signal.explanation = f"Arbitration failed ({error_category}): {str(e)}"
            signal.rejection_reason = error_category

        return signal

    async def _enrich_with_funding_rate(self, signal: Signal, symbol: str) -> Signal:
        """
        Enrich signal with funding rate signal.

        This method:
        1. Calls FundingRateStrategy to analyze funding rate
        2. Updates signal.funding_rate and signal.funding_rate_signal
        3. Returns enriched signal object

        Args:
            signal: Signal object to enrich
            symbol: Trading pair symbol (e.g., "BTCUSDT")

        Returns:
            Enriched signal object with funding rate fields set
        """
        try:
            # Call funding rate strategy
            funding_result = await self.funding_rate_strategy.analyze(symbol)

            if funding_result:
                signal.funding_rate = funding_result["funding_rate"]
                signal.funding_rate_signal = funding_result["signal"]

                logger.info(
                    "funding_rate_enrichment_complete",
                    signal_id=str(signal.id),
                    market=signal.market,
                    funding_rate=str(funding_result["funding_rate"]),
                    funding_rate_signal=funding_result["signal"]
                )
            else:
                logger.debug(
                    "no_funding_rate_signal",
                    signal_id=str(signal.id),
                    market=signal.market
                )

        except Exception as e:
            logger.error(
                "funding_rate_enrichment_error",
                error=str(e),
                signal_id=str(signal.id),
                market=signal.market
            )
            # Fallback: Leave funding rate fields as None

        return signal

    @staticmethod
    def _normalize_kline_fields(klines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将DataHub返回的K线字段名转换为FeatureEngineer期望的字段名

        DataHub字段: open_price, close_price, high_price, low_price, volume
        FeatureEngineer字段: open, close, high, low, volume

        Args:
            klines: DataHub返回的K线列表

        Returns:
            字段名已转换的K线列表
        """
        normalized = []
        for kline in klines:
            normalized.append({
                'open': kline.get('open_price'),
                'close': kline.get('close_price'),
                'high': kline.get('high_price'),
                'low': kline.get('low_price'),
                'volume': kline.get('volume'),
                # 保留其他字段（如果需要）
                'open_time': kline.get('open_time'),
                'close_time': kline.get('close_time'),
            })
        return normalized

    async def _get_multifreq_and_reference_klines(
        self,
        symbol: str,
        primary_klines: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        获取v2.7模型所需的额外K线数据（4h K线 + 参考币种K线）

        设计目的：
        - 为v2.7模型提供跨币种特征计算所需的数据
        - 使用DataHub批量接口，减少网络往返次数
        - 实现降级策略：单个参考币种数据缺失不影响整体流程

        Args:
            symbol: 目标币种符号 (e.g., "BTCUSDT")
            primary_klines: 目标币种的1h K线数据（已获取）

        Returns:
            字典包含：
            - secondary_klines: 目标币种的4h K线（25条）
            - reference_klines: 参考币种的1h K线字典 {symbol: [klines]}
            - missing_reference_symbols: 缺失的参考币种列表

            如果获取失败，返回None
        """
        # 定义参考币种（v2.7模型需要的5个参考币种）
        REFERENCE_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]

        try:
            # 构建批量查询请求
            queries = [
                {"symbol": symbol, "interval": "4h", "limit": 25},  # 目标币种4h K线
            ]

            # 添加参考币种查询（排除目标币种自身）
            for ref_symbol in REFERENCE_SYMBOLS:
                if ref_symbol != symbol:  # 避免重复查询
                    queries.append({"symbol": ref_symbol, "interval": "1h", "limit": 100})

            # 调用DataHub批量接口
            async with httpx.AsyncClient(timeout=settings.DATAHUB_TIMEOUT) as client:
                url = f"{settings.DATAHUB_BASE_URL}/v1/klines/batch"
                response = await client.post(url, json={"queries": queries})
                response.raise_for_status()
                batch_result = response.json()

            # 解析结果
            results = batch_result.get("results", {})
            errors = batch_result.get("errors", {})

            # 提取4h K线
            secondary_key = f"{symbol}:4h"
            secondary_klines_raw = results.get(secondary_key, [])

            if not secondary_klines_raw:
                logger.error(
                    "v2_7_secondary_klines_missing",
                    symbol=symbol,
                    error=errors.get(secondary_key, "No data returned"),
                    message="Failed to fetch 4h klines for target symbol"
                )
                return None

            # 转换4h K线字段名
            secondary_klines = self._normalize_kline_fields(secondary_klines_raw)

            # 提取参考币种K线
            reference_klines = {}
            missing_symbols = []

            for ref_symbol in REFERENCE_SYMBOLS:
                if ref_symbol == symbol:
                    # 目标币种使用已有的1h K线（已经是转换后的格式）
                    reference_klines[ref_symbol] = primary_klines
                else:
                    key = f"{ref_symbol}:1h"
                    if key in results and results[key]:
                        # 转换参考币种K线字段名
                        reference_klines[ref_symbol] = self._normalize_kline_fields(results[key])
                    else:
                        # 数据缺失，记录WARNING
                        logger.warning(
                            "v2_7_reference_symbol_missing",
                            ref_symbol=ref_symbol,
                            target_symbol=symbol,
                            error=errors.get(key, "No data returned"),
                            message=f"Reference symbol {ref_symbol} data missing, will use neutral values (0.0)"
                        )
                        missing_symbols.append(ref_symbol)
                        reference_klines[ref_symbol] = []  # 空列表，特征计算时会处理

            # 如果所有参考币种数据都缺失，记录ERROR
            if len(missing_symbols) == len(REFERENCE_SYMBOLS):
                logger.error(
                    "v2_7_all_reference_symbols_missing",
                    target_symbol=symbol,
                    message="All reference symbols data missing. Consider degrading to v1 model."
                )
                # 仍然返回数据，让特征计算方法处理（使用中性值）

            logger.info(
                "v2_7_additional_data_fetched",
                target_symbol=symbol,
                secondary_klines_count=len(secondary_klines),
                reference_symbols_count=len([k for k, v in reference_klines.items() if v]),
                missing_symbols_count=len(missing_symbols)
            )

            return {
                "secondary_klines": secondary_klines,
                "reference_klines": reference_klines,
                "missing_reference_symbols": missing_symbols
            }

        except Exception as e:
            logger.error(
                "v2_7_additional_data_fetch_error",
                error=str(e),
                target_symbol=symbol,
                message="Failed to fetch additional data for v2.7 model"
            )
            return None

    async def _get_secondary_klines(
        self,
        symbol: str,
        interval: str,
        limit: int
    ) -> Optional[List[Dict[str, Any]]]:
        """
        获取单个币种的K线数据（用于v2.6模型）

        Args:
            symbol: 币种符号
            interval: 时间周期 (e.g., "4h")
            limit: K线数量

        Returns:
            K线数据列表，失败返回None
        """
        try:
            async with httpx.AsyncClient(timeout=settings.DATAHUB_TIMEOUT) as client:
                url = f"{settings.DATAHUB_BASE_URL}/v1/klines/{symbol}/{interval}"
                params = {"limit": limit}
                response = await client.get(url, params=params)
                response.raise_for_status()
                klines = response.json()

                if not klines:
                    logger.warning(
                        "secondary_klines_empty",
                        symbol=symbol,
                        interval=interval,
                        message="No klines data returned"
                    )
                    return None

                return klines

        except Exception as e:
            logger.error(
                "secondary_klines_fetch_error",
                error=str(e),
                symbol=symbol,
                interval=interval,
                message="Failed to fetch secondary klines"
            )
            return None

