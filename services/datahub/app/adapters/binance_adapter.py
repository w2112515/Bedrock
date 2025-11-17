"""
Binance API Adapter

Provides interface to fetch K-line (candlestick) data from Binance API.
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from shared.utils.logger import setup_logging

# Load environment variables
load_dotenv()

logger = setup_logging("binance_adapter")


class BinanceAdapter:
    """
    Adapter for Binance API to fetch K-line data.
    """
    
    # Supported intervals
    INTERVALS = [
        Client.KLINE_INTERVAL_1MINUTE,
        Client.KLINE_INTERVAL_3MINUTE,
        Client.KLINE_INTERVAL_5MINUTE,
        Client.KLINE_INTERVAL_15MINUTE,
        Client.KLINE_INTERVAL_30MINUTE,
        Client.KLINE_INTERVAL_1HOUR,
        Client.KLINE_INTERVAL_2HOUR,
        Client.KLINE_INTERVAL_4HOUR,
        Client.KLINE_INTERVAL_6HOUR,
        Client.KLINE_INTERVAL_8HOUR,
        Client.KLINE_INTERVAL_12HOUR,
        Client.KLINE_INTERVAL_1DAY,
        Client.KLINE_INTERVAL_3DAY,
        Client.KLINE_INTERVAL_1WEEK,
        Client.KLINE_INTERVAL_1MONTH,
    ]
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialize Binance adapter.
        
        Args:
            api_key: Binance API key (optional, defaults to env var)
            api_secret: Binance API secret (optional, defaults to env var)
        """
        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET")
        
        if not self.api_key or not self.api_secret:
            logger.warning("Binance API credentials not configured")
            self.client = None
        else:
            try:
                self.client = Client(self.api_key, self.api_secret)
                logger.info("Binance client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Binance client: {e}")
                self.client = None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def get_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """
        Fetch K-line data from Binance.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            interval: K-line interval (e.g., "1m", "1h", "1d")
            start_time: Start time for data fetch
            end_time: End time for data fetch
            limit: Maximum number of K-lines to fetch (default 500, max 1000)

        Returns:
            List of K-line data dictionaries

        Raises:
            ValueError: If client is not initialized or parameters are invalid
            BinanceAPIException: If Binance API returns an error
        """
        if not self.client:
            raise ValueError("Binance client not initialized. Check API credentials.")
        
        if interval not in self.INTERVALS:
            raise ValueError(f"Invalid interval: {interval}. Must be one of {self.INTERVALS}")
        
        if limit > 1000:
            logger.warning(f"Limit {limit} exceeds maximum 1000, using 1000")
            limit = 1000
        
        try:
            # Convert datetime to milliseconds timestamp
            start_str = None
            end_str = None
            if start_time:
                start_str = str(int(start_time.timestamp() * 1000))
            if end_time:
                end_str = str(int(end_time.timestamp() * 1000))
            
            logger.info(f"Fetching K-lines for {symbol} with interval {interval}, limit {limit}")
            
            # Fetch K-lines from Binance
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                startTime=start_str,
                endTime=end_str,
                limit=limit
            )
            
            # Transform Binance K-line format to our format
            result = []
            for kline in klines:
                result.append({
                    "symbol": symbol,
                    "interval": interval,
                    "open_time": int(kline[0]),
                    "close_time": int(kline[6]),
                    "open_price": float(kline[1]),
                    "high_price": float(kline[2]),
                    "low_price": float(kline[3]),
                    "close_price": float(kline[4]),
                    "volume": float(kline[5]),
                    "quote_volume": float(kline[7]),
                    "trade_count": int(kline[8]),
                    "taker_buy_base_volume": float(kline[9]),
                    "taker_buy_quote_volume": float(kline[10]),
                    "source": "binance"
                })
            
            logger.info(f"Successfully fetched {len(result)} K-lines for {symbol}")
            return result
            
        except BinanceAPIException as e:
            logger.error(f"Binance API error: {e.status_code} - {e.message}")
            # FIXED: Import and raise CustomBinanceAPIException
            from services.datahub.app.exceptions import BinanceAPIException as CustomBinanceAPIException
            raise CustomBinanceAPIException(
                message=e.message,
                details={
                    "provider": "binance",
                    "status_code": e.status_code,
                    "symbol": symbol,
                    "interval": interval
                }
            )
        except BinanceRequestException as e:
            logger.error(f"Binance request error: {e.message}")
            from services.datahub.app.exceptions import ExternalAPIException
            raise ExternalAPIException(
                message=f"Binance request error: {e.message}",
                details={"provider": "binance", "symbol": symbol}
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching K-lines: {e}")
            raise
    
    def get_historical_klines(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical K-line data (can fetch more than 1000 records).
        
        This method automatically handles pagination to fetch large datasets.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            interval: K-line interval (e.g., "1m", "1h", "1d")
            start_time: Start time for data fetch
            end_time: End time for data fetch (defaults to now)
        
        Returns:
            List of K-line data dictionaries
        """
        if not self.client:
            raise ValueError("Binance client not initialized. Check API credentials.")
        
        if interval not in self.INTERVALS:
            raise ValueError(f"Invalid interval: {interval}. Must be one of {self.INTERVALS}")
        
        if not end_time:
            end_time = datetime.utcnow()
        
        try:
            logger.info(f"Fetching historical K-lines for {symbol} from {start_time} to {end_time}")
            
            # Use Binance's historical klines method (handles pagination)
            klines = self.client.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_str=start_time.strftime("%d %b %Y %H:%M:%S"),
                end_str=end_time.strftime("%d %b %Y %H:%M:%S")
            )
            
            # Transform to our format
            result = []
            for kline in klines:
                result.append({
                    "symbol": symbol,
                    "interval": interval,
                    "open_time": int(kline[0]),
                    "close_time": int(kline[6]),
                    "open_price": float(kline[1]),
                    "high_price": float(kline[2]),
                    "low_price": float(kline[3]),
                    "close_price": float(kline[4]),
                    "volume": float(kline[5]),
                    "quote_volume": float(kline[7]),
                    "trade_count": int(kline[8]),
                    "taker_buy_base_volume": float(kline[9]),
                    "taker_buy_quote_volume": float(kline[10]),
                    "source": "binance"
                })
            
            logger.info(f"Successfully fetched {len(result)} historical K-lines for {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching historical K-lines: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((BinanceAPIException, BinanceRequestException)),
        reraise=True
    )
    def get_funding_rate(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch funding rate data from Binance Futures API.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            start_time: Start time for data fetch
            end_time: End time for data fetch
            limit: Maximum number of records to fetch (default 100, max 1000)

        Returns:
            List of funding rate data dictionaries:
            [
                {
                    "symbol": "BTCUSDT",
                    "funding_time": 1731744000000,
                    "funding_rate": "0.00010000",
                    "mark_price": "89500.00000000"
                }
            ]

        Raises:
            ValueError: If client is not initialized or parameters are invalid
            BinanceAPIException: If Binance API returns an error
        """
        if not self.client:
            raise ValueError("Binance client not initialized. Check API credentials.")

        if limit > 1000:
            logger.warning(f"Limit {limit} exceeds maximum 1000, using 1000")
            limit = 1000

        try:
            # Convert datetime to milliseconds timestamp
            start_str = None
            end_str = None
            if start_time:
                start_str = int(start_time.timestamp() * 1000)
            if end_time:
                end_str = int(end_time.timestamp() * 1000)

            logger.info(f"Fetching funding rates for {symbol}, limit {limit}")

            # Call Binance Futures API
            # Note: Using requests directly as python-binance may not have this method
            import requests

            base_url = "https://fapi.binance.com"
            endpoint = "/fapi/v1/fundingRate"

            params = {
                "symbol": symbol,
                "limit": limit
            }
            if start_str:
                params["startTime"] = start_str
            if end_str:
                params["endTime"] = end_str

            response = requests.get(f"{base_url}{endpoint}", params=params, timeout=10)
            response.raise_for_status()

            funding_rates = response.json()

            # Transform to our format
            result = []
            for rate in funding_rates:
                result.append({
                    "symbol": rate["symbol"],
                    "funding_time": int(rate["fundingTime"]),
                    "funding_rate": rate["fundingRate"],
                    "mark_price": rate.get("markPrice", "0")
                })

            logger.info(f"Successfully fetched {len(result)} funding rates for {symbol}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching funding rates: {e}")
            from services.datahub.app.exceptions import ExternalAPIException
            raise ExternalAPIException(
                message=f"Binance Futures API request error: {str(e)}",
                details={"provider": "binance_futures", "symbol": symbol}
            )
        except Exception as e:
            logger.error(f"Error fetching funding rates: {e}")
            raise

    def get_exchange_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get exchange information (trading rules, symbols, etc.).

        Args:
            symbol: Optional symbol to get info for specific pair

        Returns:
            Exchange information dictionary
        """
        if not self.client:
            raise ValueError("Binance client not initialized. Check API credentials.")

        try:
            if symbol:
                info = self.client.get_symbol_info(symbol)
            else:
                info = self.client.get_exchange_info()

            return info

        except Exception as e:
            logger.error(f"Error fetching exchange info: {e}")
            raise
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get information for a specific trading symbol.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")

        Returns:
            Symbol information dictionary or None if not found
        """
        if not self.client:
            raise ValueError("Binance client not initialized. Check API credentials.")

        try:
            info = self.client.get_symbol_info(symbol)
            return info
        except Exception as e:
            logger.error(f"Error fetching symbol info for {symbol}: {e}")
            return None

    def test_connection(self) -> bool:
        """
        Test connection to Binance API.

        Returns:
            True if connection is successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            self.client.ping()
            logger.info("Binance API connection test successful")
            return True
        except Exception as e:
            logger.error(f"Binance API connection test failed: {e}")
            return False

