# ML模型部署指南

## 目录
1. [概述](#概述)
2. [模型版本说明](#模型版本说明)
3. [部署前准备](#部署前准备)
4. [部署步骤](#部署步骤)
5. [健康检查](#健康检查)
6. [回滚方案](#回滚方案)
7. [监控和告警](#监控和告警)
8. [常见问题](#常见问题)

---

## 概述

本指南描述了如何在Project Bedrock中部署和切换ML模型版本。系统支持三个模型版本：

- **v1**: 13个基础技术指标特征
- **v2.6**: 19个多频特征（multifreq-full baseline）
- **v2.7**: 30个特征（19个多频 + 11个跨币种特征）

所有模型版本都支持快速切换和回滚，无需修改代码。

---

## 模型版本说明

### v1 模型（当前生产版本）
- **特征数量**: 13个基础技术指标
- **数据需求**: 1h K线数据（100条）
- **性能**: AUC ≈ 0.55
- **稳定性**: 已在生产环境运行稳定
- **适用场景**: 基础信号生成，低延迟要求

### v2.6 模型
- **特征数量**: 19个多频特征
- **数据需求**: 1h K线（100条）+ 4h K线（25条）
- **性能**: AUC ≈ 0.58
- **稳定性**: 实验验证稳定
- **适用场景**: 多时间周期分析

### v2.7 模型（推荐）
- **特征数量**: 30个特征（19个多频 + 11个跨币种）
- **数据需求**: 
  - 目标币种：1h K线（100条）+ 4h K线（25条）
  - 参考币种：BTC/ETH/BNB/SOL/ADA的1h K线（各100条）
- **性能**: AUC = 0.5972（seed=5926，性能最优）
- **稳定性**: EXCELLENT（AUC=0.5939±0.0021，CV=0.35%）
- **适用场景**: 跨币种关联分析，高精度信号生成
- **降级策略**: 参考币种数据缺失时使用中性值（0.0）

---

## 部署前准备

### 1. 确认模型文件存在

```bash
# v2.7模型文件
ls -lh services/decision_engine/models/xgboost_signal_confidence_v2_7_seed_5926.pkl
ls -lh services/decision_engine/models/feature_names_v2_7.json
ls -lh services/decision_engine/models/stability_stats_v2_7.json
ls -lh services/decision_engine/models/best_hyperparameters_v2_7.json
```

### 2. 备份当前配置

```bash
# 备份.env文件
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# 备份docker-compose.yml（如果有修改）
cp docker-compose.yml docker-compose.yml.backup.$(date +%Y%m%d_%H%M%S)
```

### 3. 确认DataHub服务健康

```bash
# 检查DataHub健康状态
curl http://localhost:8001/health

# 测试批量K线接口（v2.7模型需要）
curl -X POST http://localhost:8001/v1/klines/batch \
  -H "Content-Type: application/json" \
  -d '{
    "queries": [
      {"symbol": "BTCUSDT", "interval": "1h", "limit": 100},
      {"symbol": "BTCUSDT", "interval": "4h", "limit": 25}
    ]
  }'
```

---

## 部署步骤

### 方案A：本地/测试环境部署（推荐先测试）

#### 步骤1：修改环境变量

编辑 `.env` 文件，修改以下配置：

```bash
# 切换到v2.7模型
ML_MODEL_VERSION=v2_7
ML_MODEL_PATH=services/decision_engine/models/xgboost_signal_confidence_v2_7_seed_5926.pkl
ML_FEATURE_NAMES_PATH=services/decision_engine/models/feature_names_v2_7.json
```

#### 步骤2：运行健康检查

```bash
# 运行模型健康检查脚本
python services/decision_engine/scripts/health_check_model.py
```

**预期输出**：
```
================================================================================
ML Model Health Check - Version: v2_7
================================================================================

[1/7] Checking model file: services/decision_engine/models/xgboost_signal_confidence_v2_7_seed_5926.pkl
  ✅ PASSED: Model file exists (XXX.XX KB)
[2/7] Checking feature names file: services/decision_engine/models/feature_names_v2_7.json
  ✅ PASSED: Feature names file exists
[3/7] Loading model...
  ✅ PASSED: Model loaded successfully
[4/7] Loading feature names...
  ✅ PASSED: Feature names loaded (30 features)
[5/7] Validating feature count...
  ✅ PASSED: Feature count matches (30 features)
[6/7] Testing model prediction with random features...
  ✅ PASSED: Model prediction successful (score: XX.XX)
[7/7] Running regression tests...
  ✅ Test 1/3 PASSED: Bullish (看涨) (score: XX.XX, expected: 70-100)
  ✅ Test 2/3 PASSED: Neutral (中性) (score: XX.XX, expected: 40-60)
  ✅ Test 3/3 PASSED: Bearish (看跌) (score: XX.XX, expected: 0-40)

================================================================================
Health Check Summary
================================================================================
✅ ALL CHECKS PASSED - Model is healthy and ready for deployment!
================================================================================
```

#### 步骤3：重启DecisionEngine服务

```bash
# 重启服务
docker-compose restart decision_engine

# 查看启动日志
docker-compose logs -f decision_engine
```

**预期日志**：
```
INFO: ML Model Configuration: Version=v2_7, Path=services/decision_engine/models/xgboost_signal_confidence_v2_7_seed_5926.pkl
INFO: ML adapter initialized successfully (version: v2_7)
```

#### 步骤4：验证服务健康

```bash
# 检查服务健康状态
curl http://localhost:8002/health

# 手动触发信号生成（测试）
curl -X POST http://localhost:8002/api/v1/signals/generate
```

#### 步骤5：监控日志和指标

```bash
# 实时监控DecisionEngine日志
docker-compose logs -f decision_engine | grep -E "ml_enrichment|v2_7"

# 检查是否有参考币种数据缺失的警告
docker-compose logs decision_engine | grep "v2_7_reference_symbol_missing"

# 检查是否有错误
docker-compose logs decision_engine | grep "ERROR"
```

**关键日志示例**：

✅ **正常情况**：
```
INFO: ml_enrichment_success model_version=v2_7 ml_score=75.5 symbol=BTCUSDT
INFO: v2_7_additional_data_fetched target_symbol=BTCUSDT secondary_klines_count=25 reference_symbols_count=5 missing_symbols_count=0
```

⚠️ **降级情况（部分参考币种缺失）**：
```
WARNING: v2_7_reference_symbol_missing ref_symbol=ADAUSDT target_symbol=BTCUSDT message="Reference symbol ADAUSDT data missing, will use neutral values (0.0)"
INFO: ml_enrichment_success model_version=v2_7 ml_score=72.3 symbol=BTCUSDT
```

❌ **错误情况（所有参考币种缺失）**：
```
ERROR: v2_7_all_reference_symbols_missing target_symbol=BTCUSDT message="All reference symbols data missing. Consider degrading to v1 model."
```

---

### 方案B：生产环境部署

⚠️ **重要提示**：只有在本地/测试环境验证成功后，才能部署到生产环境！

#### 步骤1：选择低流量时段

- 建议在非交易高峰期部署（例如：UTC 00:00-04:00）
- 提前通知相关团队

#### 步骤2：执行部署

按照"方案A"的步骤1-5执行部署。

#### 步骤3：灰度验证（可选）

如果生产环境支持灰度发布，可以先在部分实例上部署v2.7模型：

```bash
# 只重启部分实例
docker-compose up -d --scale decision_engine=2
```

#### 步骤4：全量部署

确认灰度验证成功后，全量部署：

```bash
# 重启所有实例
docker-compose restart decision_engine
```

---

## 健康检查

### 自动健康检查

系统会在启动时自动进行以下检查：

1. **配置验证**：验证 `ML_MODEL_VERSION` 是否合法（v1/v2_6/v2_7）
2. **模型加载**：验证模型文件是否可加载
3. **特征名称加载**：验证特征名称文件是否存在

如果任何检查失败，服务将无法启动，并输出详细错误信息。

### 手动健康检查

```bash
# 运行完整健康检查
python services/decision_engine/scripts/health_check_model.py

# 检查服务健康状态
curl http://localhost:8002/health
```

### 回归测试

健康检查脚本包含3个回归测试用例：

1. **看涨场景**：强势技术指标 + 正向市场情绪 → 预期高分（70-100）
2. **中性场景**：中性技术指标 + 中性市场情绪 → 预期中等分（40-60）
3. **看跌场景**：弱势技术指标 + 负向市场情绪 → 预期低分（0-40）

如果任何测试用例失败，说明模型行为异常，需要进一步排查。

---

## 回滚方案

### 快速回滚到v1模型

如果v2.7模型出现问题，可以快速回滚到v1模型：

#### 步骤1：修改环境变量

编辑 `.env` 文件：

```bash
# 回滚到v1模型
ML_MODEL_VERSION=v1
ML_MODEL_PATH=services/decision_engine/models/xgboost_signal_confidence_v1.pkl
ML_FEATURE_NAMES_PATH=services/decision_engine/models/feature_names.json
```

#### 步骤2：重启服务

```bash
# 重启DecisionEngine服务
docker-compose restart decision_engine

# 验证服务健康
curl http://localhost:8002/health
```

#### 步骤3：验证回滚成功

```bash
# 检查日志，确认使用v1模型
docker-compose logs decision_engine | grep "ML Model Configuration"
```

**预期输出**：
```
INFO: ML Model Configuration: Version=v1, Path=services/decision_engine/models/xgboost_signal_confidence_v1.pkl
```

### 回滚时间估算

- **配置修改**: 1分钟
- **服务重启**: 30秒
- **验证**: 2分钟
- **总计**: 约4分钟

---

## 监控和告警

### 关键指标

1. **模型预测成功率**：监控 `ml_enrichment_success` 日志的频率
2. **参考币种数据缺失率**：监控 `v2_7_reference_symbol_missing` 警告的频率
3. **模型预测延迟**：监控信号生成的总延迟
4. **模型输出分布**：监控ML分数的分布（应该在0-100范围内）

### 告警规则

建议配置以下告警：

1. **错误告警**：
   - `v2_7_all_reference_symbols_missing` 出现 → 立即告警
   - `ml_enrichment_error` 出现 → 立即告警

2. **警告告警**：
   - `v2_7_reference_symbol_missing` 频率 > 20% → 告警
   - 模型预测延迟 > 2秒 → 告警

3. **性能告警**：
   - 信号生成失败率 > 5% → 告警
   - ML分数异常（全部为50.0） → 告警

---

## 常见问题

### Q1: 部署v2.7模型后，信号生成变慢了？

**A**: v2.7模型需要获取额外的K线数据（4h + 参考币种），会增加一定延迟。正常情况下，延迟应该在1秒以内。如果延迟超过2秒，请检查：

1. DataHub服务是否健康
2. 网络连接是否正常
3. 是否有大量参考币种数据缺失

### Q2: 看到大量 `v2_7_reference_symbol_missing` 警告？

**A**: 这表示某些参考币种的K线数据缺失。可能的原因：

1. DataHub数据采集延迟
2. 某些币种暂时没有交易数据
3. DataHub服务异常

**解决方案**：
- 检查DataHub日志，确认数据采集是否正常
- 如果问题持续，考虑回滚到v1模型

### Q3: 如何验证v2.7模型是否正常工作？

**A**: 运行以下检查：

```bash
# 1. 运行健康检查脚本
python services/decision_engine/scripts/health_check_model.py

# 2. 手动触发信号生成
curl -X POST http://localhost:8002/api/v1/signals/generate

# 3. 检查日志
docker-compose logs decision_engine | grep "ml_enrichment_success"
```

### Q4: v2.7模型的ML分数和v1模型差异很大？

**A**: 这是正常的。v2.7模型使用了更多特征（30个 vs 13个），预测结果会有差异。建议：

1. 运行回归测试，确认模型行为符合预期
2. 对比v1和v2.7的信号质量（准确率、收益率等）
3. 如果v2.7表现不佳，可以回滚到v1

### Q5: 如何切换到v2.6模型？

**A**: 修改 `.env` 文件：

```bash
ML_MODEL_VERSION=v2_6
ML_MODEL_PATH=services/decision_engine/models/xgboost_signal_confidence_v2_6.pkl
ML_FEATURE_NAMES_PATH=services/decision_engine/models/feature_names_v2_6.json
```

然后重启服务：

```bash
docker-compose restart decision_engine
```

---

## 附录

### 模型文件清单

```
services/decision_engine/models/
├── xgboost_signal_confidence_v1.pkl              # v1模型文件
├── feature_names.json                            # v1特征名称
├── xgboost_signal_confidence_v2_7_seed_5926.pkl  # v2.7模型文件（推荐）
├── feature_names_v2_7.json                       # v2.7特征名称
├── stability_stats_v2_7.json                     # v2.7稳定性统计
└── best_hyperparameters_v2_7.json                # v2.7超参数
```

### 相关文档

- [模型降级策略文档](./MODEL_DEGRADATION_STRATEGY.md)
- [特征工程文档](./FEATURE_ENGINEERING.md)
- [DecisionEngine架构文档](./ARCHITECTURE.md)

---

**最后更新**: 2025-11-16
**维护者**: Project Bedrock Team


