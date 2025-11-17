"""
初始化仲裁配置脚本

功能：
1. 检查数据库中是否已存在活动的仲裁配置
2. 如果不存在，从环境变量读取默认权重并插入数据库
3. 验证权重总和为1.0
4. 提供清晰的成功/失败提示

使用方法：
    python scripts/init_arbiter_config.py
"""

import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.utils.database import SessionLocal
from services.decision_engine.app.models.arbitration_config import ArbitrationConfig
from services.decision_engine.app.core.config import settings
from shared.utils.logger import setup_logging

logger = setup_logging("init_arbiter_config")


def validate_weights(rule_weight: float, ml_weight: float, llm_weight: float) -> bool:
    """
    验证权重总和为1.0
    
    Args:
        rule_weight: 规则引擎权重
        ml_weight: ML引擎权重
        llm_weight: LLM引擎权重
        
    Returns:
        True if valid, False otherwise
    """
    total = rule_weight + ml_weight + llm_weight
    is_valid = abs(total - 1.0) < 0.0001
    
    if not is_valid:
        logger.error(
            f"权重验证失败: 总和={total:.4f} (期望=1.0000), "
            f"rule={rule_weight}, ml={ml_weight}, llm={llm_weight}"
        )
    
    return is_valid


def main():
    """初始化仲裁配置"""
    db = SessionLocal()
    
    try:
        logger.info("=" * 60)
        logger.info("开始初始化仲裁配置")
        logger.info("=" * 60)
        
        # 1. 检查是否已存在活动配置
        existing_config = db.query(ArbitrationConfig).filter_by(is_active=True).first()
        
        if existing_config:
            logger.info("✅ 数据库中已存在活动配置，跳过初始化")
            logger.info(f"   Version: {existing_config.version}")
            logger.info(f"   Rule Weight: {existing_config.rule_weight}")
            logger.info(f"   ML Weight: {existing_config.ml_weight}")
            logger.info(f"   LLM Weight: {existing_config.llm_weight}")
            logger.info(f"   Min Approval Score: {existing_config.min_approval_score}")
            logger.info(f"   Created At: {existing_config.created_at}")
            return
        
        # 2. 从环境变量读取默认权重
        rule_weight = settings.ARBITER_RULE_WEIGHT
        ml_weight = settings.ARBITER_ML_WEIGHT
        llm_weight = settings.ARBITER_LLM_WEIGHT
        min_approval_score = settings.ARBITER_MIN_APPROVAL_SCORE
        
        logger.info("从环境变量读取配置:")
        logger.info(f"   ARBITER_RULE_WEIGHT: {rule_weight}")
        logger.info(f"   ARBITER_ML_WEIGHT: {ml_weight}")
        logger.info(f"   ARBITER_LLM_WEIGHT: {llm_weight}")
        logger.info(f"   ARBITER_MIN_APPROVAL_SCORE: {min_approval_score}")
        
        # 3. 验证权重
        if not validate_weights(rule_weight, ml_weight, llm_weight):
            logger.error("❌ 权重验证失败，请检查环境变量配置")
            sys.exit(1)
        
        logger.info("✅ 权重验证通过")
        
        # 4. 计算下一个版本号
        max_version = db.query(ArbitrationConfig).count()
        next_version = max_version + 1
        
        # 5. 创建新配置
        new_config = ArbitrationConfig(
            version=next_version,
            rule_weight=Decimal(str(rule_weight)),
            ml_weight=Decimal(str(ml_weight)),
            llm_weight=Decimal(str(llm_weight)),
            min_approval_score=Decimal(str(min_approval_score)),
            adaptive_threshold_enabled=False,
            is_active=True
        )
        
        db.add(new_config)
        db.commit()
        db.refresh(new_config)
        
        logger.info("=" * 60)
        logger.info("✅ 仲裁配置初始化成功")
        logger.info("=" * 60)
        logger.info(f"   ID: {new_config.id}")
        logger.info(f"   Version: {new_config.version}")
        logger.info(f"   Rule Weight: {new_config.rule_weight}")
        logger.info(f"   ML Weight: {new_config.ml_weight}")
        logger.info(f"   LLM Weight: {new_config.llm_weight}")
        logger.info(f"   Min Approval Score: {new_config.min_approval_score}")
        logger.info(f"   Adaptive Threshold: {new_config.adaptive_threshold_enabled}")
        logger.info(f"   Is Active: {new_config.is_active}")
        logger.info(f"   Created At: {new_config.created_at}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}", exc_info=True)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

