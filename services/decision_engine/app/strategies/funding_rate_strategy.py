"""
Funding Rate Strategy

Implements funding rate-based trading signals:
1. High funding rate (>0.1%) → SHORT signal (market overheated)
2. Low funding rate (<-0.1%) → LONG signal (market oversold)
3. Neutral funding rate (-0.1% ~ 0.1%) → No signal

Includes Redis caching to reduce API calls (TTL=8 hours).
"""

import sys
import os
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
import httpx
import redis.asyncio as redis

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from services.decision_engine.app.core.config import settings

logger = setup_logging("funding_rate_strategy")


class FundingRateStrategy:
    """
    Funding rate-based trading strategy.
    
    Responsibilities:
    1. Fetch funding rate data from DataHub API
    2. Cache funding rate data in Redis (TTL=8 hours)
    3. Analyze funding rate and generate trading signals
    4. Return signal with confidence score
    
    Signal Logic:
    - High funding rate (>threshold) → SHORT signal
    - Low funding rate (<-threshold) → LONG signal
    - Neutral funding rate → None
    """
    
    def __init__(self):
        self.datahub_url = settings.DATAHUB_BASE_URL
        self.timeout = settings.DATAHUB_TIMEOUT
        self.high_threshold = settings.FUNDING_RATE_HIGH_THRESHOLD
        self.low_threshold = settings.FUNDING_RATE_LOW_THRESHOLD
        self.cache_ttl = settings.FUNDING_RATE_CACHE_TTL
        
        # Initialize Redis client
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
    
    async def analyze(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Analyze funding rate and generate trading signal.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
        
        Returns:
            Signal dictionary or None:
            {
                "signal": "LONG" | "SHORT",
                "funding_rate": Decimal,
                "confidence": float
            }
        """
        try:
            # 1. Get funding rate (with Redis caching)
            funding_rate = await self._get_funding_rate_cached(symbol)
            
            if funding_rate is None:
                logger.warning(f"No funding rate data for {symbol}")
                return None
            
            # 2. Analyze funding rate
            funding_rate_decimal = Decimal(str(funding_rate))
            
            # High funding rate → SHORT signal
            if funding_rate_decimal > self.high_threshold:
                logger.info(
                    f"High funding rate for {symbol}: {funding_rate_decimal} > {self.high_threshold}, "
                    f"generating SHORT signal"
                )
                return {
                    "signal": "SHORT",
                    "funding_rate": funding_rate_decimal,
                    "confidence": 0.7
                }
            
            # Low funding rate → LONG signal
            elif funding_rate_decimal < self.low_threshold:
                logger.info(
                    f"Low funding rate for {symbol}: {funding_rate_decimal} < {self.low_threshold}, "
                    f"generating LONG signal"
                )
                return {
                    "signal": "LONG",
                    "funding_rate": funding_rate_decimal,
                    "confidence": 0.7
                }
            
            # Neutral funding rate → No signal
            else:
                logger.debug(
                    f"Neutral funding rate for {symbol}: {funding_rate_decimal}, no signal"
                )
                return None
        
        except Exception as e:
            logger.error(f"Error analyzing funding rate for {symbol}: {e}")
            return None
    
    async def _get_funding_rate_cached(self, symbol: str) -> Optional[str]:
        """
        Get funding rate with Redis caching.
        
        Cache key format: funding_rate:{symbol}:{funding_time_hour}
        TTL: 8 hours (aligned with funding rate settlement cycle)
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Funding rate string or None
        """
        try:
            # 1. Generate cache key (aligned to current hour)
            current_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
            cache_key = f"funding_rate:{symbol}:{current_hour.isoformat()}"
            
            # 2. Check Redis cache
            cached_value = await self.redis_client.get(cache_key)
            if cached_value:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value

            # 3. Cache miss → Call DataHub API
            logger.debug(f"Cache miss for {cache_key}, calling DataHub API")
            funding_rate = await self._fetch_funding_rate_from_api(symbol)

            if funding_rate is None:
                return None

            # 4. Write to Redis cache
            await self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                funding_rate
            )
            logger.debug(f"Cached funding rate for {cache_key}, TTL={self.cache_ttl}s")

            return funding_rate

        except Exception as e:
            logger.error(f"Error getting cached funding rate for {symbol}: {e}")
            # Fallback: try to fetch from API directly
            return await self._fetch_funding_rate_from_api(symbol)

    async def _fetch_funding_rate_from_api(self, symbol: str) -> Optional[str]:
        """
        Fetch funding rate from DataHub API.

        Args:
            symbol: Trading pair symbol

        Returns:
            Funding rate string or None
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.datahub_url}/v1/funding-rates"
                params = {
                    "symbol": symbol,
                    "limit": 1  # Only need the latest funding rate
                }

                response = await client.get(url, params=params)
                response.raise_for_status()

                data = response.json()

                if not data.get("success") or not data.get("data"):
                    logger.warning(f"No funding rate data returned for {symbol}")
                    return None

                # Get the latest funding rate
                latest_rate = data["data"][0]
                funding_rate = latest_rate["funding_rate"]

                logger.info(f"Fetched funding rate for {symbol}: {funding_rate}")
                return funding_rate

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching funding rate for {symbol}: {e.response.status_code}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error fetching funding rate for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching funding rate for {symbol}: {e}")
            return None

