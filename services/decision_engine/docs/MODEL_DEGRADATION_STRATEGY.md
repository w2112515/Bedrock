# ML模型降级策略文档

## 目录
1. [概述](#概述)
2. [降级场景](#降级场景)
3. [降级策略](#降级策略)
4. [日志记录](#日志记录)
5. [监控和告警](#监控和告警)
6. [测试验证](#测试验证)

---

## 概述

本文档描述了Project Bedrock中ML模型的降级策略，确保在数据缺失或异常情况下，系统仍能正常运行并生成信号。

### 设计原则

1. **优雅降级**：数据缺失时使用中性值，而不是直接失败
2. **透明性**：所有降级行为都有详细的日志记录
3. **可监控**：降级事件可被监控和告警
4. **可回滚**：支持快速回滚到更稳定的模型版本

---

## 降级场景

### 场景1：模型文件不可用

**触发条件**：
- 模型文件不存在
- 模型文件损坏无法加载
- 特征名称文件缺失

**降级策略**：
- 使用 `ML_FALLBACK_SCORE`（默认50.0）作为ML分数
- 记录ERROR日志
- 服务继续运行，但ML模块不可用

**代码位置**：
- `services/decision_engine/app/adapters/xgboost_adapter.py`

**日志示例**：
```
ERROR: Failed to load ML model: [Errno 2] No such file or directory: 'services/decision_engine/models/xgboost_signal_confidence_v2_7.pkl'
WARNING: ML model not loaded, using fallback score: 50.0
```

---

### 场景2：参考币种数据缺失（v2.7模型）

**触发条件**：
- 某个参考币种（BTC/ETH/BNB/SOL/ADA）的K线数据缺失
- DataHub返回空数据或错误

**降级策略**：

#### 2.1 单个参考币种缺失

**行为**：
- 对应的跨币种特征值设为 **0.0（中性值）**
- 记录WARNING日志
- 继续使用其他可用的参考币种数据
- 模型仍然可以预测（使用部分特征）

**影响的特征**：
- 如果BTC数据缺失：`btc_return_1h_lag`, `btc_return_2h_lag`, `btc_return_4h_lag`, `btc_return_24h_lag`, `btc_trend_4h` = 0.0
- 如果ETH数据缺失：`eth_return_1h_lag`, `eth_return_2h_lag` = 0.0
- 市场整体特征（`market_return_1h`, `market_bullish_ratio`）使用可用币种计算

**代码位置**：
- `services/decision_engine/app/engines/rule_engine.py` - `_get_multifreq_and_reference_klines()`
- `services/decision_engine/app/services/feature_engineer.py` - `calculate_features_crosspair()`

**日志示例**：
```
WARNING: v2_7_reference_symbol_missing ref_symbol=ADAUSDT target_symbol=BTCUSDT error="No data returned" message="Reference symbol ADAUSDT data missing, will use neutral values (0.0)"
INFO: ml_enrichment_success model_version=v2_7 ml_score=72.3 symbol=BTCUSDT missing_reference_symbols=['ADAUSDT']
```

#### 2.2 所有参考币种缺失

**行为**：
- 所有跨币种特征值设为 **0.0（中性值）**
- 记录ERROR日志
- 模型仍然可以预测（但只使用19个多频特征）
- 建议考虑回滚到v1模型

**代码位置**：
- `services/decision_engine/app/engines/rule_engine.py` - `_get_multifreq_and_reference_klines()`

**日志示例**：
```
ERROR: v2_7_all_reference_symbols_missing target_symbol=BTCUSDT message="All reference symbols data missing. Consider degrading to v1 model."
INFO: ml_enrichment_success model_version=v2_7 ml_score=50.5 symbol=BTCUSDT missing_reference_symbols=['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
```

---

### 场景3：4h K线数据缺失（v2.6/v2.7模型）

**触发条件**：
- 目标币种的4h K线数据缺失
- DataHub返回空数据或错误

**降级策略**：
- **不使用ML模型**（因为缺少必需的多频特征）
- 记录ERROR日志
- 使用 `ML_FALLBACK_SCORE`（默认50.0）作为ML分数
- 信号生成继续，但ML置信度为降级值

**代码位置**：
- `services/decision_engine/app/engines/rule_engine.py` - `_enrich_with_ml_score()`

**日志示例**：
```
ERROR: v2_7_secondary_klines_missing symbol=BTCUSDT error="No data returned" message="Failed to fetch 4h klines for target symbol"
WARNING: ML enrichment skipped due to missing data, using fallback score: 50.0
```

---

### 场景4：市场整体趋势特征降级（v2.7模型）

**触发条件**：
- 少于3个参考币种有可用数据

**降级策略**：
- `market_return_1h` = 0.0（中性值）
- `market_bullish_ratio` = 0.5（50%中性值）
- 记录WARNING日志

**代码位置**：
- `services/decision_engine/app/services/feature_engineer.py` - `calculate_features_crosspair()`

**日志示例**：
```
WARNING: Insufficient reference symbols for market trend calculation (available: 2, required: 3), using neutral values
```

---

## 降级策略

### 中性值选择原则

| 特征类型 | 中性值 | 理由 |
|---------|--------|------|
| 收益率特征 (return) | 0.0 | 表示无涨跌 |
| 趋势指标 (trend) | 0.0 | 表示无明确趋势 |
| 比率特征 (ratio) | 0.5 | 表示50%中性状态 |
| 相关性特征 (correlation) | 0.0 | 表示无相关性 |
| ML分数 (fallback_score) | 50.0 | 表示中性置信度 |

### 降级优先级

1. **优先级1（最高）**：使用部分可用数据 + 中性值
   - 例如：5个参考币种中有3个可用，使用3个计算市场趋势

2. **优先级2（中等）**：使用降级特征值（0.0或0.5）
   - 例如：所有参考币种缺失，所有跨币种特征 = 0.0

3. **优先级3（最低）**：使用fallback分数（50.0）
   - 例如：模型无法加载，或必需数据完全缺失

---

## 日志记录

### 日志级别

| 场景 | 日志级别 | 示例 |
|------|---------|------|
| 模型加载失败 | ERROR | `Failed to load ML model` |
| 所有参考币种缺失 | ERROR | `v2_7_all_reference_symbols_missing` |
| 4h K线缺失 | ERROR | `v2_7_secondary_klines_missing` |
| 单个参考币种缺失 | WARNING | `v2_7_reference_symbol_missing` |
| 市场趋势降级 | WARNING | `Insufficient reference symbols for market trend` |
| ML enrichment成功 | INFO | `ml_enrichment_success` |

### 日志字段

所有降级相关日志都包含以下字段：

- `model_version`: 模型版本（v1/v2_6/v2_7）
- `symbol`: 目标币种
- `error`: 错误信息（如果有）
- `message`: 人类可读的描述
- `missing_reference_symbols`: 缺失的参考币种列表（v2.7）

---

## 监控和告警

### 关键指标

1. **参考币种数据缺失率**
   ```
   rate(v2_7_reference_symbol_missing_total[5m])
   ```

2. **所有参考币种缺失事件**
   ```
   increase(v2_7_all_reference_symbols_missing_total[5m]) > 0
   ```

3. **ML enrichment失败率**
   ```
   rate(ml_enrichment_error_total[5m]) / rate(ml_enrichment_attempts_total[5m])
   ```

4. **Fallback分数使用率**
   ```
   rate(ml_fallback_score_used_total[5m]) / rate(signals_generated_total[5m])
   ```

### 告警规则

#### 告警1：高频参考币种缺失

**条件**：
```
rate(v2_7_reference_symbol_missing_total[5m]) > 0.2
```

**严重程度**: WARNING

**处理建议**：
1. 检查DataHub服务健康状态
2. 检查数据采集是否正常
3. 如果问题持续，考虑回滚到v1模型

#### 告警2：所有参考币种缺失

**条件**：
```
increase(v2_7_all_reference_symbols_missing_total[5m]) > 0
```

**严重程度**: CRITICAL

**处理建议**：
1. 立即检查DataHub服务
2. 检查网络连接
3. 考虑立即回滚到v1模型

#### 告警3：ML enrichment失败率过高

**条件**：
```
rate(ml_enrichment_error_total[5m]) / rate(ml_enrichment_attempts_total[5m]) > 0.1
```

**严重程度**: CRITICAL

**处理建议**：
1. 检查模型文件是否完整
2. 检查DataHub服务
3. 考虑回滚到v1模型

---

## 测试验证

### 单元测试

测试用例应覆盖以下场景：

1. **测试单个参考币种缺失**
   ```python
   reference_klines = {
       'BTCUSDT': [...],  # 有数据
       'ETHUSDT': [],     # 缺失
       'BNBUSDT': [...],
       'SOLUSDT': [...],
       'ADAUSDT': [...]
   }
   features = calculate_features_crosspair(...)
   assert features['eth_return_1h_lag'] == 0.0
   ```

2. **测试所有参考币种缺失**
   ```python
   reference_klines = {
       'BTCUSDT': [],
       'ETHUSDT': [],
       'BNBUSDT': [],
       'SOLUSDT': [],
       'ADAUSDT': []
   }
   features = calculate_features_crosspair(...)
   assert all(features[f] == 0.0 for f in cross_pair_features)
   ```

3. **测试市场趋势降级**
   ```python
   # 只有2个币种有数据（少于3个）
   reference_klines = {
       'BTCUSDT': [...],
       'ETHUSDT': [...],
       'BNBUSDT': [],
       'SOLUSDT': [],
       'ADAUSDT': []
   }
   features = calculate_features_crosspair(...)
   assert features['market_return_1h'] == 0.0
   assert features['market_bullish_ratio'] == 0.5
   ```

### 集成测试

1. **模拟DataHub返回空数据**
2. **模拟DataHub返回错误**
3. **模拟部分参考币种数据缺失**
4. **验证日志记录是否正确**

---

**最后更新**: 2025-11-16  
**维护者**: Project Bedrock Team

