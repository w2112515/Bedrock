"""
Adapters for external ML/LLM engines.

This package contains adapter implementations for integrating
machine learning models and large language models into the
DecisionEngine service.
"""

from .ml_model_interface import MLModelInterface
from .llm_interface import LLMInterface, SentimentResult

__all__ = ["MLModelInterface", "LLMInterface", "SentimentResult"]

