"""
ML Model Interface - Abstract base class for ML model adapters.

This module defines the contract that all ML model adapters must implement.
Following the Adapter Pattern and Dependency Inversion Principle.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional


class MLModelInterface(ABC):
    """
    Abstract interface for ML model adapters.
    
    This interface allows the DecisionEngine to work with different
    ML models (XGBoost, LightGBM, PyTorch, etc.) without coupling
    to specific implementations.
    
    Design Principles:
    - Interface Segregation: Only essential methods
    - Dependency Inversion: RuleEngine depends on abstraction
    - Open/Closed: Easy to add new model types
    """
    
    @abstractmethod
    def predict(self, features: Dict[str, float]) -> Optional[float]:
        """
        Predict confidence score from features.
        
        Args:
            features: Dictionary of feature name -> value pairs
                     Example: {"rsi_14": 65.5, "macd": 0.023, ...}
        
        Returns:
            Confidence score in range [0, 100], or None if prediction fails
            - 0-30: Low confidence (bearish)
            - 30-70: Medium confidence (neutral)
            - 70-100: High confidence (bullish)
        
        Raises:
            No exceptions should be raised. Return None on failure.
        """
        pass
    
    @abstractmethod
    def is_loaded(self) -> bool:
        """
        Check if the model is successfully loaded and ready for predictions.
        
        Returns:
            True if model is loaded, False otherwise
        """
        pass

