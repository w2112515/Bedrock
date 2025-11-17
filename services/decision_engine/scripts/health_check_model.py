#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML模型健康检查脚本

功能：
1. 验证模型文件是否存在且可加载
2. 验证特征名称文件是否存在且匹配
3. 测试模型预测功能（随机特征）
4. 回归测试：验证模型输出是否在预期范围内（看涨/中性/看跌场景）

使用方法：
    python services/decision_engine/scripts/health_check_model.py

环境变量：
    ML_MODEL_VERSION: 模型版本 (v1/v2_6/v2_7)
    ML_MODEL_PATH: 模型文件路径
    ML_FEATURE_NAMES_PATH: 特征名称文件路径
"""

import os
import sys
import json
import pickle
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from services.decision_engine.app.core.config import settings, MLModelVersion


# 定义状态符号（兼容Windows控制台）
PASS_SYMBOL = "[PASS]"
FAIL_SYMBOL = "[FAIL]"
SUCCESS_SYMBOL = "[SUCCESS]"
WARNING_SYMBOL = "[WARNING]"


class ModelHealthChecker:
    """ML模型健康检查器"""
    
    def __init__(self):
        self.model_version = settings.ML_MODEL_VERSION
        self.model_path = Path(settings.ML_MODEL_PATH)
        self.feature_names_path = Path(settings.ML_FEATURE_NAMES_PATH)
        self.model = None
        self.feature_names = None
        self.errors = []
        self.warnings = []
    
    def run_all_checks(self) -> bool:
        """运行所有健康检查"""
        print("=" * 80)
        print(f"ML Model Health Check - Version: {self.model_version}")
        print("=" * 80)
        print()
        
        # 1. 检查模型文件
        if not self._check_model_file_exists():
            return False
        
        # 2. 检查特征名称文件
        if not self._check_feature_names_file_exists():
            return False
        
        # 3. 加载模型
        if not self._load_model():
            return False
        
        # 4. 加载特征名称
        if not self._load_feature_names():
            return False
        
        # 5. 验证特征数量匹配
        if not self._validate_feature_count():
            return False
        
        # 6. 测试模型预测（随机特征）
        if not self._test_model_prediction():
            return False
        
        # 7. 回归测试（3个场景）
        if not self._run_regression_tests():
            return False
        
        # 输出总结
        self._print_summary()
        
        return len(self.errors) == 0
    
    def _check_model_file_exists(self) -> bool:
        """检查模型文件是否存在"""
        print(f"[1/7] Checking model file: {self.model_path}")

        if not self.model_path.exists():
            self.errors.append(f"Model file not found: {self.model_path}")
            print(f"  {FAIL_SYMBOL} FAILED: Model file not found")
            return False

        print(f"  {PASS_SYMBOL} PASSED: Model file exists ({self.model_path.stat().st_size / 1024:.2f} KB)")
        return True

    def _check_feature_names_file_exists(self) -> bool:
        """检查特征名称文件是否存在"""
        print(f"[2/7] Checking feature names file: {self.feature_names_path}")

        if not self.feature_names_path.exists():
            self.errors.append(f"Feature names file not found: {self.feature_names_path}")
            print(f"  {FAIL_SYMBOL} FAILED: Feature names file not found")
            return False

        print(f"  {PASS_SYMBOL} PASSED: Feature names file exists")
        return True

    def _load_model(self) -> bool:
        """加载模型"""
        print(f"[3/7] Loading model...")

        try:
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            print(f"  {PASS_SYMBOL} PASSED: Model loaded successfully")
            return True
        except Exception as e:
            self.errors.append(f"Failed to load model: {str(e)}")
            print(f"  {FAIL_SYMBOL} FAILED: {str(e)}")
            return False

    def _load_feature_names(self) -> bool:
        """加载特征名称"""
        print(f"[4/7] Loading feature names...")

        try:
            with open(self.feature_names_path, 'r') as f:
                self.feature_names = json.load(f)
            print(f"  {PASS_SYMBOL} PASSED: Feature names loaded ({len(self.feature_names)} features)")
            return True
        except Exception as e:
            self.errors.append(f"Failed to load feature names: {str(e)}")
            print(f"  {FAIL_SYMBOL} FAILED: {str(e)}")
            return False

    def _validate_feature_count(self) -> bool:
        """验证特征数量是否匹配模型版本"""
        print(f"[5/7] Validating feature count...")

        expected_counts = {
            MLModelVersion.V1.value: 13,
            MLModelVersion.V2_6.value: 19,
            MLModelVersion.V2_7.value: 30
        }

        expected_count = expected_counts.get(self.model_version)
        actual_count = len(self.feature_names)

        if expected_count != actual_count:
            self.errors.append(
                f"Feature count mismatch: expected {expected_count} for {self.model_version}, "
                f"got {actual_count}"
            )
            print(f"  {FAIL_SYMBOL} FAILED: Expected {expected_count} features, got {actual_count}")
            return False

        print(f"  {PASS_SYMBOL} PASSED: Feature count matches ({actual_count} features)")
        return True

    def _test_model_prediction(self) -> bool:
        """测试模型预测功能（使用随机特征）"""
        print(f"[6/7] Testing model prediction with random features...")

        try:
            import numpy as np
            import pandas as pd

            # 生成随机特征（中性值附近）
            random_features = np.random.randn(len(self.feature_names)) * 0.1
            features_df = pd.DataFrame([random_features], columns=self.feature_names)

            # 预测
            prediction = self.model.predict(features_df)[0]

            # 验证输出范围（0-100）
            if not (0 <= prediction <= 100):
                self.errors.append(f"Prediction out of range: {prediction} (expected 0-100)")
                print(f"  {FAIL_SYMBOL} FAILED: Prediction {prediction} out of range [0, 100]")
                return False

            print(f"  {PASS_SYMBOL} PASSED: Model prediction successful (score: {prediction:.2f})")
            return True

        except Exception as e:
            self.errors.append(f"Model prediction failed: {str(e)}")
            print(f"  {FAIL_SYMBOL} FAILED: {str(e)}")
            return False

    def _run_regression_tests(self) -> bool:
        """运行回归测试（3个场景）"""
        print(f"[7/7] Running regression tests...")

        test_cases = self._get_regression_test_cases()
        all_passed = True

        for i, test_case in enumerate(test_cases, 1):
            scenario = test_case["scenario"]
            features = test_case["features"]
            expected_range = test_case["expected_range"]

            try:
                import pandas as pd

                # 构建特征DataFrame
                features_df = pd.DataFrame([features], columns=self.feature_names)

                # 预测
                prediction = self.model.predict(features_df)[0]

                # 验证输出范围
                min_score, max_score = expected_range
                if min_score <= prediction <= max_score:
                    print(f"  {PASS_SYMBOL} Test {i}/{len(test_cases)} PASSED: {scenario} (score: {prediction:.2f}, expected: {min_score}-{max_score})")
                else:
                    self.errors.append(
                        f"Regression test failed for '{scenario}': "
                        f"score {prediction:.2f} not in expected range [{min_score}, {max_score}]"
                    )
                    print(f"  {FAIL_SYMBOL} Test {i}/{len(test_cases)} FAILED: {scenario} (score: {prediction:.2f}, expected: {min_score}-{max_score})")
                    all_passed = False

            except Exception as e:
                self.errors.append(f"Regression test failed for '{scenario}': {str(e)}")
                print(f"  {FAIL_SYMBOL} Test {i}/{len(test_cases)} FAILED: {scenario} - {str(e)}")
                all_passed = False

        return all_passed

    def _get_regression_test_cases(self) -> List[Dict[str, Any]]:
        """
        获取回归测试用例

        设计原则：
        - 看涨场景：强势技术指标 + 正向市场情绪 -> 预期高分（70-100）
        - 中性场景：中性技术指标 + 中性市场情绪 -> 预期中等分（40-60）
        - 看跌场景：弱势技术指标 + 负向市场情绪 -> 预期低分（0-40）
        """
        # 根据模型版本返回不同的测试用例
        if self.model_version == MLModelVersion.V1.value:
            return self._get_v1_test_cases()
        elif self.model_version == MLModelVersion.V2_6.value:
            return self._get_v2_6_test_cases()
        elif self.model_version == MLModelVersion.V2_7.value:
            return self._get_v2_7_test_cases()
        else:
            return []

    def _get_v1_test_cases(self) -> List[Dict[str, Any]]:
        """v1模型测试用例（13个基础特征）"""
        return [
            {
                "scenario": "Bullish (看涨)",
                "features": [0.05, 0.03, 0.02, 70.0, 60.0, 1.5, 0.8, 0.7, 0.6, 0.04, 0.03, 0.02, 1.2],
                "expected_range": (70, 100)
            },
            {
                "scenario": "Neutral (中性)",
                "features": [0.0, 0.0, 0.0, 50.0, 50.0, 1.0, 0.5, 0.5, 0.5, 0.0, 0.0, 0.0, 1.0],
                "expected_range": (40, 60)
            },
            {
                "scenario": "Bearish (看跌)",
                "features": [-0.05, -0.03, -0.02, 30.0, 40.0, 0.8, 0.3, 0.3, 0.4, -0.04, -0.03, -0.02, 0.8],
                "expected_range": (0, 40)
            }
        ]

    def _get_v2_6_test_cases(self) -> List[Dict[str, Any]]:
        """v2.6模型测试用例（19个多频特征）"""
        return [
            {
                "scenario": "Bullish (看涨)",
                "features": [0.05, 0.03, 0.02, 70.0, 60.0, 1.5, 0.8, 0.7, 0.6, 0.04, 0.03, 0.02, 1.2,
                            0.06, 0.04, 75.0, 65.0, 1.6, 0.85],
                "expected_range": (70, 100)
            },
            {
                "scenario": "Neutral (中性)",
                "features": [0.0, 0.0, 0.0, 50.0, 50.0, 1.0, 0.5, 0.5, 0.5, 0.0, 0.0, 0.0, 1.0,
                            0.0, 0.0, 50.0, 50.0, 1.0, 0.5],
                "expected_range": (40, 60)
            },
            {
                "scenario": "Bearish (看跌)",
                "features": [-0.05, -0.03, -0.02, 30.0, 40.0, 0.8, 0.3, 0.3, 0.4, -0.04, -0.03, -0.02, 0.8,
                            -0.06, -0.04, 25.0, 35.0, 0.7, 0.25],
                "expected_range": (0, 40)
            }
        ]

    def _get_v2_7_test_cases(self) -> List[Dict[str, Any]]:
        """v2.7模型测试用例（30个特征：19个多频 + 11个跨币种）"""
        return [
            {
                "scenario": "Bullish (看涨)",
                "features": [
                    # 13个基础特征
                    0.05, 0.03, 0.02, 70.0, 60.0, 1.5, 0.8, 0.7, 0.6, 0.04, 0.03, 0.02, 1.2,
                    # 6个多频特征
                    0.06, 0.04, 75.0, 65.0, 1.6, 0.85,
                    # 11个跨币种特征
                    0.04, 0.03, 0.05, 0.08, 1.0,  # BTC leading (5)
                    0.03, 0.02,  # ETH leading (2)
                    0.04, 0.7,  # Market overall (2)
                    0.8, 0.75  # Inter-coin correlation (2)
                ],
                "expected_range": (70, 100)
            },
            {
                "scenario": "Neutral (中性)",
                "features": [
                    # 13个基础特征
                    0.0, 0.0, 0.0, 50.0, 50.0, 1.0, 0.5, 0.5, 0.5, 0.0, 0.0, 0.0, 1.0,
                    # 6个多频特征
                    0.0, 0.0, 50.0, 50.0, 1.0, 0.5,
                    # 11个跨币种特征
                    0.0, 0.0, 0.0, 0.0, 0.0,  # BTC leading (5)
                    0.0, 0.0,  # ETH leading (2)
                    0.0, 0.5,  # Market overall (2)
                    0.0, 0.0  # Inter-coin correlation (2)
                ],
                "expected_range": (40, 60)
            },
            {
                "scenario": "Bearish (看跌)",
                "features": [
                    # 13个基础特征
                    -0.05, -0.03, -0.02, 30.0, 40.0, 0.8, 0.3, 0.3, 0.4, -0.04, -0.03, -0.02, 0.8,
                    # 6个多频特征
                    -0.06, -0.04, 25.0, 35.0, 0.7, 0.25,
                    # 11个跨币种特征
                    -0.04, -0.03, -0.05, -0.08, 0.0,  # BTC leading (5)
                    -0.03, -0.02,  # ETH leading (2)
                    -0.04, 0.3,  # Market overall (2)
                    -0.8, -0.75  # Inter-coin correlation (2)
                ],
                "expected_range": (0, 40)
            }
        ]

    def _print_summary(self):
        """打印健康检查总结"""
        print()
        print("=" * 80)
        print("Health Check Summary")
        print("=" * 80)

        if len(self.errors) == 0 and len(self.warnings) == 0:
            print(f"{SUCCESS_SYMBOL} ALL CHECKS PASSED - Model is healthy and ready for deployment!")
        else:
            if len(self.errors) > 0:
                print(f"{FAIL_SYMBOL} FAILED - {len(self.errors)} error(s) found:")
                for i, error in enumerate(self.errors, 1):
                    print(f"  {i}. {error}")

            if len(self.warnings) > 0:
                print(f"{WARNING_SYMBOL} WARNING - {len(self.warnings)} warning(s) found:")
                for i, warning in enumerate(self.warnings, 1):
                    print(f"  {i}. {warning}")

        print("=" * 80)


def main():
    """主函数"""
    checker = ModelHealthChecker()
    success = checker.run_all_checks()

    # 返回退出码（0=成功，1=失败）
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()


