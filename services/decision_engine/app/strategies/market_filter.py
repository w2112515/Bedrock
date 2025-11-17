"""
Market Filter Strategy

Filters markets based on trend conditions and onchain data.
Calls DataHub Service to retrieve K-line and onchain data.
Implements degradation logic for onchain data failures.
"""

import sys
import os
from typing import List, Dict, Any, Optional
import httpx
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from services.decision_engine.app.core.config import settings

logger = setup_logging("market_filter")


class MarketFilter:
    """
    Market filtering strategy.
    
    Responsibilities:
    1. Call DataHub Service to get K-line data
    2. Call DataHub Service to get onchain data (with degradation)
    3. Filter markets based on trend conditions
    4. Calculate onchain signal scores
    """
    
    def __init__(self):
        self.datahub_url = settings.DATAHUB_BASE_URL
        self.timeout = settings.DATAHUB_TIMEOUT
        
    async def filter_markets(
        self,
        symbols: List[str],
        interval: str = "1h",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Filter markets based on trend conditions.

        注意（v2.7模型支持）：
        - 本方法只返回1h K线数据（primary_klines）
        - v2.7模型需要的额外数据（4h K线 + 参考币种K线）由RuleEngine通过DataHub批量接口获取
        - 这样设计的原因：
          1. MarketFilter专注于市场筛选，不关心模型版本
          2. RuleEngine根据模型版本动态获取所需数据
          3. 避免MarketFilter与模型版本耦合

        Args:
            symbols: List of trading symbols (e.g., ["BTCUSDT", "ETHUSDT"])
            interval: K-line interval (default: "1h")
            limit: Number of K-lines to retrieve (default: 100)

        Returns:
            List of filtered markets with data:
            [
                {
                    "symbol": "BTCUSDT",
                    "kline_data": [...],  # 1h K线数据
                    "onchain_data": {...},
                    "trend_score": 75.0,
                    "onchain_score": 20.0,
                    "total_score": 95.0
                }
            ]
        """
        filtered_markets = []
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for symbol in symbols:
                try:
                    # 1. Get K-line data
                    kline_data = await self._get_kline_data(client, symbol, interval, limit)
                    if not kline_data:
                        logger.warning(f"No K-line data for {symbol}, skipping")
                        continue
                    
                    # 2. Calculate trend score
                    trend_score = self._calculate_trend_score(kline_data)
                    if trend_score < settings.MIN_TREND_SCORE:
                        logger.debug(f"{symbol} trend score {trend_score} below threshold, skipping")
                        continue
                    
                    # 3. Get onchain data (with degradation)
                    onchain_result = await self.check_onchain_signals(client, symbol)
                    onchain_score = onchain_result["score"]
                    onchain_data = onchain_result["signals"]
                    
                    # 4. Calculate total score
                    total_score = trend_score + onchain_score
                    
                    filtered_markets.append({
                        "symbol": symbol,
                        "kline_data": kline_data,
                        "onchain_data": onchain_data,
                        "trend_score": trend_score,
                        "onchain_score": onchain_score,
                        "total_score": total_score
                    })
                    
                    logger.info(
                        f"Market {symbol} passed filter: "
                        f"trend={trend_score:.1f}, onchain={onchain_score:.1f}, total={total_score:.1f}"
                    )
                    
                except Exception as e:
                    logger.error(f"Error filtering market {symbol}: {e}")
                    continue
        
        # Sort by total score descending
        filtered_markets.sort(key=lambda x: x["total_score"], reverse=True)
        
        logger.info(f"Filtered {len(filtered_markets)} markets from {len(symbols)} symbols")
        return filtered_markets
    
    async def _get_kline_data(
        self,
        client: httpx.AsyncClient,
        symbol: str,
        interval: str,
        limit: int
    ) -> Optional[List[Dict[str, Any]]]:
        """Get K-line data from DataHub Service."""
        try:
            # Fixed: Use correct DataHub API endpoint format
            url = f"{self.datahub_url}/v1/klines/{symbol}/{interval}"
            params = {"limit": limit}

            response = await client.get(url, params=params)
            response.raise_for_status()

            # DataHub returns a list of K-line objects directly
            data = response.json()
            return data if isinstance(data, list) else []

        except Exception as e:
            logger.error(f"Failed to get K-line data for {symbol}: {e}")
            return None
    
    async def check_onchain_signals(
        self, 
        client: httpx.AsyncClient, 
        symbol: str
    ) -> Dict[str, Any]:
        """
        Check onchain data signals with degradation logic.
        
        Returns:
            {
                "score": 20.0,
                "signals": {
                    "large_transfers": 8,
                    "exchange_netflow": -1500.5,
                    "smart_money_flow": 250.3,
                    "active_addresses_growth": 0.25
                }
            }
            
        If onchain data is unavailable, returns score=0.0 and signals=None.
        """
        try:
            # Extract base symbol (e.g., "BTCUSDT" -> "BTC")
            base_symbol = symbol.replace("USDT", "").replace("BUSD", "")
            
            url = f"{self.datahub_url}/v1/onchain/summary"
            params = {"symbol": base_symbol}
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Calculate onchain score
            score = 0.0
            signals = {}
            
            # Large transfers
            large_transfers = data.get("large_transfers_count", 0)
            if large_transfers >= settings.ONCHAIN_LARGE_TRANSFERS_THRESHOLD:
                score += settings.ONCHAIN_LARGE_TRANSFERS_SCORE
            signals["large_transfers"] = large_transfers
            
            # Exchange netflow (negative = outflow)
            netflow = data.get("exchange_netflow", 0.0)
            if netflow < -settings.ONCHAIN_NETFLOW_THRESHOLD:
                score += settings.ONCHAIN_NETFLOW_SCORE
            signals["exchange_netflow"] = netflow
            
            # Smart money flow
            smart_money = data.get("smart_money_flow", 0.0)
            if smart_money > settings.ONCHAIN_SMART_MONEY_THRESHOLD:
                score += settings.ONCHAIN_SMART_MONEY_SCORE
            signals["smart_money_flow"] = smart_money
            
            # Active addresses growth
            active_growth = data.get("active_addresses_growth", 0.0)
            if active_growth > settings.ONCHAIN_ACTIVE_ADDRESSES_THRESHOLD:
                score += settings.ONCHAIN_ACTIVE_ADDRESSES_SCORE
            signals["active_addresses_growth"] = active_growth
            
            logger.info(f"Onchain signals for {symbol}: score={score:.1f}, signals={signals}")
            return {"score": score, "signals": signals}
            
        except Exception as e:
            # Degradation: return zero score but don't fail the entire process
            logger.warning(f"Onchain data unavailable for {symbol}, using degradation: {e}")
            return {"score": 0.0, "signals": None}
    
    def _calculate_trend_score(self, kline_data: List[Dict[str, Any]]) -> float:
        """
        Calculate trend score based on K-line data.
        
        Scoring criteria:
        1. MA trend (40 points): Price above MA20
        2. Volume increase (30 points): Recent volume > average volume
        3. Price momentum (30 points): Recent price change > 0
        
        Returns:
            Trend score (0-100)
        """
        if len(kline_data) < 20:
            return 0.0
        
        score = 0.0
        
        try:
            # Get recent data
            recent_klines = kline_data[-20:]
            latest_kline = recent_klines[-1]
            
            # 1. MA trend (40 points)
            close_prices = [float(k["close_price"]) for k in recent_klines]
            ma20 = sum(close_prices) / len(close_prices)
            latest_close = close_prices[-1]
            
            if latest_close > ma20:
                score += 40.0
                logger.debug(f"MA trend positive: close={latest_close:.2f} > MA20={ma20:.2f}")
            
            # 2. Volume increase (30 points)
            volumes = [float(k["volume"]) for k in recent_klines]
            avg_volume = sum(volumes[:-5]) / len(volumes[:-5])  # Average of older volumes
            recent_volume = sum(volumes[-5:]) / 5  # Average of recent 5 volumes
            
            if recent_volume > avg_volume * settings.MIN_VOLUME_INCREASE_RATIO:
                score += 30.0
                logger.debug(f"Volume increased: recent={recent_volume:.2f} > avg={avg_volume:.2f}")
            
            # 3. Price momentum (30 points)
            price_change = (close_prices[-1] - close_prices[-5]) / close_prices[-5]
            if price_change > 0:
                momentum_score = min(30.0, price_change * 1000)  # Scale to 0-30
                score += momentum_score
                logger.debug(f"Price momentum positive: change={price_change:.4f}")
            
        except Exception as e:
            logger.error(f"Error calculating trend score: {e}")
            return 0.0
        
        return score

