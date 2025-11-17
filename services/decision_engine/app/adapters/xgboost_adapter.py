"""
XGBoost Adapter - Implementation of MLModelInterface for XGBoost models.

This adapter handles:
1. Model loading from disk
2. Feature transformation
3. Prediction with confidence scoring
4. Graceful degradation on failures
"""

import joblib
import json
from pathlib import Path
from typing import Dict, Optional
import structlog

from .ml_model_interface import MLModelInterface

logger = structlog.get_logger()


class XGBoostAdapter(MLModelInterface):
    """
    XGBoost model adapter with automatic fallback on load failure.
    
    Features:
    - Lazy loading: Model loaded on initialization
    - Graceful degradation: Returns None if model unavailable
    - Feature validation: Ensures correct feature order
    - Logging: All operations logged for debugging
    
    Example:
        adapter = XGBoostAdapter(
            model_path="models/xgboost_v1.pkl",
            fallback_score=50.0
        )
        
        if adapter.is_loaded():
            score = adapter.predict(features)
    """
    
    def __init__(
        self,
        model_path: str,
        fallback_score: float = 50.0,
        feature_names_path: Optional[str] = None
    ):
        """
        Initialize XGBoost adapter.

        Args:
            model_path: Path to the pickled XGBoost model file
            fallback_score: Score to use when model is unavailable (not used in predict)
            feature_names_path: Path to feature names JSON file (optional)
                               如果不指定，默认使用 model_path 同目录下的 feature_names.json

        为什么需要 feature_names_path 参数：
        - 支持多版本模型（v1/v2_6/v2_7）使用不同的特征名称文件
        - 通过环境变量 ML_FEATURE_NAMES_PATH 动态指定
        - 便于快速切换模型版本，无需修改代码
        """
        self.model_path = Path(model_path)
        self.fallback_score = fallback_score
        self.feature_names_path = Path(feature_names_path) if feature_names_path else None
        self.model = None
        self.feature_names = None

        # Attempt to load model on initialization
        self._load_model()
    
    def _load_model(self):
        """
        Load XGBoost model and feature names from disk.
        
        Implements graceful degradation (Task 2.1.8):
        - If model file not found: Log warning, continue without model
        - If loading fails: Log warning, continue without model
        - No exceptions raised to caller
        """
        try:
            # Check if model file exists
            if not self.model_path.exists():
                logger.warning(
                    "ml_model_not_found",
                    model_path=str(self.model_path),
                    fallback_score=self.fallback_score,
                    message="Model file not found. ML predictions will return None."
                )
                return
            
            # Load model
            self.model = joblib.load(self.model_path)
            logger.info(
                "ml_model_loaded",
                model_path=str(self.model_path),
                message="XGBoost model loaded successfully"
            )

            # Load feature names (for feature ordering)
            # 优先使用指定的 feature_names_path，否则使用默认路径
            if self.feature_names_path:
                feature_names_path = self.feature_names_path
            else:
                feature_names_path = self.model_path.parent / "feature_names.json"

            if feature_names_path.exists():
                with open(feature_names_path, 'r') as f:
                    self.feature_names = json.load(f)
                logger.info(
                    "feature_names_loaded",
                    path=str(feature_names_path),
                    num_features=len(self.feature_names),
                    features=self.feature_names
                )
            else:
                logger.warning(
                    "feature_names_not_found",
                    path=str(feature_names_path),
                    message="Feature names file not found. Will use features as provided."
                )
        
        except Exception as e:
            logger.warning(
                "ml_model_load_failed",
                error=str(e),
                model_path=str(self.model_path),
                fallback_score=self.fallback_score,
                message="Failed to load ML model. ML predictions will return None."
            )
            self.model = None
    
    def predict(self, features: Dict[str, float]) -> Optional[float]:
        """
        Predict confidence score using XGBoost model.
        
        Args:
            features: Dictionary of feature name -> value pairs
        
        Returns:
            Confidence score [0-100], or None if model unavailable or prediction fails
        
        Implementation:
        1. Check if model is loaded
        2. Convert features dict to DataFrame
        3. Ensure correct feature order
        4. Predict probability
        5. Convert to 0-100 scale
        """
        # Check if model is available
        if not self.is_loaded():
            logger.debug(
                "ml_prediction_skipped",
                reason="model_not_loaded"
            )
            return None
        
        try:
            # Convert features to DataFrame
            import pandas as pd
            feature_df = pd.DataFrame([features])
            
            # Ensure correct feature order (if feature_names available)
            if self.feature_names:
                # Check for missing features
                missing_features = set(self.feature_names) - set(features.keys())
                if missing_features:
                    logger.warning(
                        "ml_prediction_missing_features",
                        missing=list(missing_features),
                        message="Some features are missing. Prediction may be inaccurate."
                    )
                    # Fill missing features with 0
                    for feat in missing_features:
                        feature_df[feat] = 0.0
                
                # Reorder columns to match training
                feature_df = feature_df[self.feature_names]
            
            # Predict probability
            # Assuming binary classification: [prob_class_0, prob_class_1]
            # class_1 = bullish signal
            proba = self.model.predict_proba(feature_df)[0]
            
            # Convert to 0-100 confidence score
            # Use probability of positive class (bullish)
            confidence_score = float(proba[1] * 100)
            
            logger.debug(
                "ml_prediction_success",
                confidence_score=confidence_score,
                proba_bearish=float(proba[0]),
                proba_bullish=float(proba[1])
            )
            
            return confidence_score
        
        except Exception as e:
            logger.error(
                "ml_prediction_failed",
                error=str(e),
                features=list(features.keys()),
                message="ML prediction failed. Returning None."
            )
            return None
    
    def is_loaded(self) -> bool:
        """
        Check if model is loaded and ready.
        
        Returns:
            True if model is loaded, False otherwise
        """
        return self.model is not None

