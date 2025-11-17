# 稳定性验证执行指南

## 执行前检查

### 1. 确认环境
```bash
# 确认Python环境
python --version  # 应为Python 3.8+

# 确认依赖包
pip list | grep -E "xgboost|scikit-learn|scipy|numpy|pandas"
```

### 2. 确认数据库连接
```bash
# 测试PostgreSQL连接
python -c "from services.decision_engine.app.core.config import settings; print(settings.DATABASE_URL)"
```

## 执行步骤

### 阶段1：v2.6基线验证

#### 步骤1.1：确定性验证
```bash
cd e:\projectBedrock
python services/decision_engine/scripts/verify_determinism.py --version v2_6 --seed 42
```

**预期结果**：
- ✅ 输出 "DETERMINISM VERIFIED: AUC difference < 1e-6"
- ❌ 如果失败，检查：
  - XGBoost版本是否一致
  - 数据库数据是否被修改
  - 系统环境变量是否影响随机性

**预计时间**：10-15分钟（2次训练）

#### 步骤1.2：稳定性验证（Phase 1 + Phase 2）
```bash
python services/decision_engine/scripts/validate_stability_v2_6.py
```

**预期结果**：
- Phase 1: 生成 `best_hyperparameters_v2_6.json`
- Phase 2: 生成 `stability_stats_v2_6.json`
- 输出稳定性等级：EXCELLENT/GOOD/ACCEPTABLE/POOR

**预计时间**：50-100分钟（11次训练：1次HPO + 10次固定超参数）

#### 步骤1.3：数据一致性验证
```bash
python services/decision_engine/scripts/verify_data_consistency.py --version v2_6
```

**预期结果**：
- ✅ 输出 "DATA CONSISTENCY VERIFIED"
- ❌ 如果失败，说明数据加载存在问题，必须停止并排查

**预计时间**：< 1分钟

#### 步骤1.4：评估v2.6结果

**决策树**：
```
v2.6稳定性等级
│
├─ EXCELLENT 或 GOOD
│  └─ ✅ 继续执行阶段2（v2.7验证）
│
├─ ACCEPTABLE
│  └─ ⚠️ 记录问题，继续执行阶段2
│     但需要在最终报告中说明v2.6的稳定性也不理想
│
└─ POOR (std > 0.01)
   └─ 🚨 暂停！优先处理v2.6的稳定性问题
      1. 检查数据一致性验证结果
      2. 检查确定性验证结果
      3. 分析超参数敏感性
      4. 考虑调整模型架构或正则化参数
```

---

### 阶段2：v2.7对比验证

**前提条件**：v2.6稳定性验证通过（至少ACCEPTABLE级别）

#### 步骤2.1：确定性验证
```bash
python services/decision_engine/scripts/verify_determinism.py --version v2_7 --seed 42
```

**预计时间**：10-15分钟

#### 步骤2.2：稳定性验证（Phase 1 + Phase 2）
```bash
python services/decision_engine/scripts/validate_stability_v2_7.py
```

**预计时间**：50-100分钟

#### 步骤2.3：数据一致性验证
```bash
python services/decision_engine/scripts/verify_data_consistency.py --version v2_7
```

**预计时间**：< 1分钟

---

## 结果分析

### 1. 查看稳定性统计
```bash
# v2.6
cat services/decision_engine/models/stability_stats_v2_6.json

# v2.7
cat services/decision_engine/models/stability_stats_v2_7.json
```

### 2. 对比分析

**关键指标对比**：
| 指标 | v2.6 | v2.7 | 变化 |
|------|------|------|------|
| AUC Mean | ? | ? | ? |
| AUC Std | ? | ? | ? |
| AUC CV (%) | ? | ? | ? |
| 95% CI Width | ? | ? | ? |
| 稳定性等级 | ? | ? | ? |

### 3. 决策建议

**场景A：v2.7更稳定且性能更好**
- ✅ 推荐部署v2.7
- 更新对比分析文档
- 准备A/B测试

**场景B：v2.7性能更好但稳定性相当**
- ✅ 推荐部署v2.7
- 在报告中说明稳定性相当

**场景C：v2.7性能更好但稳定性更差**
- ⚠️ 需要权衡：
  - 如果v2.7仍为GOOD级别，可以部署
  - 如果v2.7为ACCEPTABLE或POOR，需要进一步调查

**场景D：v2.7性能和稳定性都更差**
- ❌ 不推荐部署v2.7
- 分析cross-pair特征的问题
- 考虑特征选择或正则化调整

---

## 故障排查

### 问题1：确定性验证失败（AUC差异 >= 1e-6）

**可能原因**：
1. `nthread` 未设置为1
2. `tree_method='hist'` 在多线程下有非确定性
3. 数据加载顺序不一致
4. 系统环境变量影响（如OMP_NUM_THREADS）

**解决方案**：
```python
# 在训练脚本开头添加
import os
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
```

### 问题2：数据一致性验证失败

**可能原因**：
1. 数据库在训练期间被更新
2. SQL查询结果顺序不稳定（相同timestamp的记录）
3. 数据加载逻辑有随机性

**解决方案**：
1. 确保训练期间数据库不被修改
2. 在SQL查询中添加二级排序（如ORDER BY open_time, symbol）
3. 检查数据加载代码是否有随机采样

### 问题3：稳定性验证运行时间过长

**优化方案**：
1. 使用 `--skip-hpo` 跳过Phase 1（如果已有超参数）
2. 减少训练数据量（调整date range）
3. 使用更少的种子（如5个而非10个）

---

## 预计总时间

- **v2.6完整验证**：60-120分钟
- **v2.7完整验证**：60-120分钟
- **总计**：2-4小时

**建议**：
- 在非工作时间执行（如晚上或周末）
- 使用 `nohup` 或 `screen` 避免SSH断开
- 定期检查进度（每30分钟）

---

## 下一步

验证完成后：
1. 更新 `comparison_v2_6_vs_v2_7.md` 文档
2. 生成最终对比分析报告
3. 根据结果决定是否部署v2.7
4. 如果部署，准备影子模式和A/B测试

