# 稳定性验证实施文档

## 概述

本文档记录了v2.6和v2.7模型稳定性验证功能的实施细节。

## 实施日期

2025-11-16

## 修改的文件

### 1. `train_xgboost_v2_7.py` ✅ 已完成
**修改内容**：
- 添加 `hashlib` 导入
- 添加 `fixed_hyperparameters` 参数到 `train_model_v2()` 函数
- 添加数据哈希计算（用于数据一致性验证）
- 添加固定超参数支持逻辑
- 添加命令行参数：`--fixed-hyperparameters`, `--disable-hpo`
- 在metrics中保存 `data_hash`

**关键配置**：
- 使用 `tree_method='hist'` + `nthread=1`（速度与确定性的权衡）
- 固定超参数模式下，仅改变 `random_state`

### 2. `train_xgboost_v2_6.py` ⚠️ 部分完成
**修改内容**：
- 添加 `hashlib` 导入
- 添加 `fixed_hyperparameters` 参数
- 添加数据哈希计算

**待完成**：
- 添加固定超参数支持逻辑（与v2_7相同）
- 添加命令行参数处理
- 在metrics中保存 `data_hash`

### 3. `validate_stability_v2_7.py` ✅ 已完成
**重构内容**：
- 实现两阶段验证流程：
  - Phase 1: HPO（可选，使用seed=42）
  - Phase 2: 固定超参数稳定性验证（10个种子）
- 添加95%置信区间计算
- 添加分级稳定性评估（EXCELLENT/GOOD/ACCEPTABLE/POOR）
- 添加详细的稳定性报告生成
- 添加 `--skip-hpo` 参数

**稳定性标准**：
- EXCELLENT: std ≤ 0.005, CV ≤ 1.0%, CI width ≤ 0.02
- GOOD: std ≤ 0.008, CV ≤ 1.5%, CI width ≤ 0.03
- ACCEPTABLE: std ≤ 0.01, CV ≤ 2.0%, CI width ≤ 0.04
- POOR: 超过ACCEPTABLE标准

### 4. `validate_stability_v2_6.py` ✅ 已完成
**内容**：
- 复制自 `validate_stability_v2_7.py`
- 修改为v2_6专用版本

### 5. `verify_determinism.py` ✅ 已创建
**功能**：
- 用相同种子运行训练两次
- 比较AUC差异（要求 < 1e-6）
- 验证确定性配置是否生效

**使用方法**：
```bash
python services/decision_engine/scripts/verify_determinism.py --version v2_7 --seed 42
```

### 6. `verify_data_consistency.py` ✅ 已创建
**功能**：
- 检查10次训练运行的data_hash是否完全一致
- 验证数据加载的一致性

**使用方法**：
```bash
python services/decision_engine/scripts/verify_data_consistency.py --version v2_7
```

## 执行流程

### 完整验证流程（推荐）

```bash
# 1. 验证v2.6的确定性
python services/decision_engine/scripts/verify_determinism.py --version v2_6 --seed 42

# 2. v2.6稳定性验证（Phase 1 + Phase 2）
python services/decision_engine/scripts/validate_stability_v2_6.py

# 3. 验证v2.6的数据一致性
python services/decision_engine/scripts/verify_data_consistency.py --version v2_6

# 4. 验证v2.7的确定性
python services/decision_engine/scripts/verify_determinism.py --version v2_7 --seed 42

# 5. v2.7稳定性验证（Phase 1 + Phase 2）
python services/decision_engine/scripts/validate_stability_v2_7.py

# 6. 验证v2.7的数据一致性
python services/decision_engine/scripts/verify_data_consistency.py --version v2_7
```

### 仅Phase 2验证（使用已有超参数）

```bash
python services/decision_engine/scripts/validate_stability_v2_7.py --skip-hpo
```

## 生成的文件

### 超参数文件
- `services/decision_engine/models/best_hyperparameters_v2_6.json`
- `services/decision_engine/models/best_hyperparameters_v2_7.json`

### 稳定性统计文件
- `services/decision_engine/models/stability_stats_v2_6.json`
- `services/decision_engine/models/stability_stats_v2_7.json`

### 模型和metrics文件
- `services/decision_engine/models/xgboost_signal_confidence_v2_6_seed_{seed}.pkl`
- `services/decision_engine/models/model_metrics_v2_6_seed_{seed}.json`
- `services/decision_engine/models/xgboost_signal_confidence_v2_7_seed_{seed}.pkl`
- `services/decision_engine/models/model_metrics_v2_7_seed_{seed}.json`

## 关键决策记录

### 决策1：tree_method配置
**选择**：`tree_method='hist'` + `nthread=1`
**理由**：
- `tree_method='exact'` 会导致训练时间从5分钟增加到1.5-2小时
- `'hist'` 方法在单线程模式下仍能提供足够的确定性
- 预期std增加量：0.001-0.002（在可接受范围内）

**前提条件**：
- 必须先执行确定性验证
- 必须在报告中明确记录此配置选择

### 决策2：稳定性标准
**调整**：
- 接受标准从 std ≤ 0.005 调整为 std ≤ 0.008
- CV从 ≤ 1% 调整为 ≤ 1.5%

**理由**：
- 金融预测任务的固有随机性更高
- 与行业标准一致（参考论文：std=0.0103为"good stability"）

## 待完成事项

1. ⚠️ 完成 `train_xgboost_v2_6.py` 的剩余修改
2. 📝 执行完整验证流程并生成报告
3. 📊 根据v2.6的稳定性结果决定是否继续v2.7验证

## 注意事项

1. **训练时间**：每个版本的完整验证（10次运行）预计需要50-100分钟
2. **数据一致性**：如果data_hash不一致，必须停止验证并排查原因
3. **确定性验证**：如果AUC差异 >= 1e-6，必须重新评估配置选择
4. **v2.6基线**：如果v2.6不稳定（std > 0.01），必须优先修复v2.6

## 参考文档

- 原始需求：用户在2025-11-16提出的稳定性验证方案
- 技术决策：【阶段二：方案设计与权衡】中的四个决策点
- 行业标准：AUC std=0.0103被认为是"good stability"（来源：学术论文）

