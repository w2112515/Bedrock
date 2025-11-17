"""
DecisionEngine HTTP Client.

Handles communication with DecisionEngine service for signal generation.
"""

import httpx
import logging
from typing import Optional, Dict
from decimal import Decimal
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

logger = logging.getLogger(__name__)


class DecisionEngineClient:
    """
    Client for communicating with DecisionEngine service.
    
    Responsibilities:
    - Call DecisionEngine's signal generation API
    - Handle HTTP errors and timeouts
    - Implement retry logic with exponential backoff
    - Parse and validate signal responses
    
    Note:
    - DecisionEngine internally fetches K-line data from DataHub
    - We only need to pass market symbol and force_analysis flag
    """
    
    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize DecisionEngineClient.
        
        Args:
            base_url: DecisionEngine base URL (e.g., "http://decision_engine:8002")
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        reraise=True
    )
    async def generate_signal(
        self,
        market: str,
        force_analysis: bool = True
    ) -> Optional[Dict]:
        """
        Call DecisionEngine to generate trading signal.
        
        DecisionEngine will internally:
        1. Fetch K-line data from DataHub (1h, 4h, reference pairs)
        2. Run MarketFilter to filter markets
        3. Run PullbackEntryStrategy to analyze entry signals
        4. Run ML/LLM adapters if enabled
        5. Run DecisionArbiter to make final decision
        
        Args:
            market: Trading pair (e.g., "BTCUSDT")
            force_analysis: Force analysis even if recent signal exists
        
        Returns:
            Signal dict with:
            - id: Signal ID
            - signal_type: "PULLBACK_BUY", "OOPS_BUY", "OOPS_SELL"
            - entry_price: Suggested entry price
            - stop_loss_price: Stop loss price
            - profit_target_price: Profit target price
            - ml_confidence_score: ML confidence score (optional)
            - llm_sentiment: LLM sentiment (optional)
            
            Returns None if no signal or error occurred.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Prepare request payload
                payload = {
                    "market": market,
                    "force_analysis": force_analysis
                }
                
                logger.info(
                    f"Calling DecisionEngine: market={market}, "
                    f"force_analysis={force_analysis}"
                )
                
                # Call DecisionEngine API
                response = await client.post(
                    f"{self.base_url}/v1/signals/generate",
                    json=payload
                )
                
                # Handle response
                if response.status_code == 200:
                    data = response.json()
                    signal = self._parse_signal_response(data)
                    
                    if signal:
                        logger.info(
                            f"Signal generated: {signal['signal_type']} "
                            f"at {signal['entry_price']}"
                        )
                        return signal
                    else:
                        logger.debug("Failed to parse signal response")
                        return None
                
                elif response.status_code == 404:
                    logger.debug(
                        f"No signal generated for {market} (normal case)"
                    )
                    return None
                
                else:
                    logger.error(
                        f"DecisionEngine error: status={response.status_code}, "
                        f"body={response.text}"
                    )
                    return None
        
        except httpx.TimeoutException:
            logger.error(
                f"DecisionEngine timeout after {self.timeout}s: market={market}"
            )
            raise
        
        except httpx.ConnectError as e:
            logger.error(f"DecisionEngine connection error: {e}")
            raise
        
        except Exception as e:
            logger.error(
                f"Unexpected error calling DecisionEngine: {e}",
                exc_info=True
            )
            return None

    def _parse_signal_response(self, data: Dict) -> Optional[Dict]:
        """
        Parse and validate signal response from DecisionEngine.

        Args:
            data: Response data from DecisionEngine API

        Returns:
            Parsed signal dict or None if invalid
        """
        try:
            # Validate required fields
            required_fields = [
                "signal_type",
                "entry_price",
                "stop_loss_price",
                "profit_target_price"
            ]

            if not all(field in data for field in required_fields):
                logger.warning(
                    f"Invalid signal response: missing required fields. "
                    f"Got: {list(data.keys())}"
                )
                return None

            # Parse signal
            signal = {
                "signal_type": data["signal_type"],
                "entry_price": Decimal(str(data["entry_price"])),
                "stop_loss_price": Decimal(str(data["stop_loss_price"])),
                "profit_target_price": Decimal(str(data["profit_target_price"])),
            }

            # Optional fields (use .get() for safe access)
            if "id" in data:
                signal["signal_id"] = data["id"]

            if "ml_confidence_score" in data and data["ml_confidence_score"] is not None:
                signal["ml_confidence_score"] = float(data["ml_confidence_score"])

            if "llm_sentiment" in data and data["llm_sentiment"] is not None:
                signal["llm_sentiment"] = data["llm_sentiment"]

            if "rule_engine_score" in data:
                signal["rule_engine_score"] = float(data["rule_engine_score"])

            if "suggested_position_weight" in data:
                signal["suggested_position_weight"] = float(data["suggested_position_weight"])

            return signal

        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing signal response: {e}", exc_info=True)
            return None

