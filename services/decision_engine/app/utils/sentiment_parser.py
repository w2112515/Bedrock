"""
Sentiment Parser

Parses LLM API responses and extracts sentiment analysis results.
Handles various JSON formats and validates output.

Phase 2 - Task 2.2.5: Part of QwenAdapter implementation
"""

import json
import re
from typing import Optional

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from services.decision_engine.app.adapters.llm_interface import SentimentResult
from shared.utils.logger import setup_logging

logger = setup_logging("sentiment_parser")


class SentimentParser:
    """
    LLM response parser.
    
    Features:
    1. Extract JSON from Qwen API response
    2. Validate sentiment field (BULLISH/BEARISH/NEUTRAL)
    3. Validate confidence field (0-100)
    4. Handle malformed responses
    
    Design Principles:
    - Single Responsibility Principle (SRP): Only responsible for parsing
    - Robustness: Handles multiple JSON formats
    """
    
    VALID_SENTIMENTS = {"BULLISH", "BEARISH", "NEUTRAL"}
    
    def parse(self, api_response: dict) -> Optional[SentimentResult]:
        """
        Parse Qwen API response.
        
        Args:
            api_response: Complete Qwen API response
            
        Returns:
            SentimentResult or None if parsing fails
            
        Example:
            parser = SentimentParser()
            result = parser.parse({
                "output": {
                    "choices": [{
                        "message": {
                            "content": '{"sentiment": "BULLISH", "confidence": 85, ...}'
                        }
                    }]
                }
            })
        """
        try:
            # 1. Extract LLM output text
            output_text = self._extract_output_text(api_response)
            if not output_text:
                logger.error("Failed to extract output text from API response")
                return None
            
            # 2. Extract JSON
            json_data = self._extract_json(output_text)
            if not json_data:
                logger.error(f"Failed to extract JSON from output: {output_text[:200]}")
                return None
            
            # 3. Validate and normalize
            result = self._validate_and_normalize(json_data)
            return result
            
        except Exception as e:
            logger.error(f"Error parsing sentiment response: {e}")
            return None
    
    def _extract_output_text(self, api_response: dict) -> Optional[str]:
        """
        Extract output text from API response.
        
        Qwen API response format:
        {
            "output": {
                "choices": [
                    {
                        "message": {
                            "content": "..."
                        }
                    }
                ]
            }
        }
        """
        try:
            return api_response["output"]["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Invalid API response structure: {e}")
            return None
    
    def _extract_json(self, text: str) -> Optional[dict]:
        """
        Extract JSON from text.
        
        Supports multiple formats:
        1. Pure JSON: {"sentiment": "BULLISH", ...}
        2. Markdown code block: ```json\n{...}\n```
        3. Mixed text: Some text {"sentiment": ...} some text
        
        Args:
            text: Text containing JSON
            
        Returns:
            Parsed JSON dict or None
        """
        # Try 1: Direct parsing
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        
        # Try 2: Extract from Markdown code block
        markdown_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if markdown_match:
            try:
                return json.loads(markdown_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try 3: Extract first complete JSON object
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _validate_and_normalize(self, json_data: dict) -> Optional[SentimentResult]:
        """
        Validate and normalize JSON data.
        
        Args:
            json_data: Parsed JSON dict
            
        Returns:
            SentimentResult or None if validation fails
        """
        try:
            # Extract fields
            sentiment = json_data.get("sentiment", "").upper()
            confidence = float(json_data.get("confidence", 50.0))
            explanation = json_data.get("explanation", "")
            
            # Validate sentiment
            if sentiment not in self.VALID_SENTIMENTS:
                logger.warning(
                    f"Invalid sentiment '{sentiment}', defaulting to NEUTRAL"
                )
                sentiment = "NEUTRAL"
            
            # Validate confidence range
            confidence = max(0.0, min(100.0, confidence))
            
            # Validate explanation length
            if len(explanation) > 200:
                explanation = explanation[:197] + "..."
            
            if not explanation:
                explanation = "无解释"
            
            return {
                "sentiment": sentiment,
                "confidence": confidence,
                "explanation": explanation
            }
            
        except (ValueError, TypeError) as e:
            logger.error(f"Error validating sentiment data: {e}")
            return None

