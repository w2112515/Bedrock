# DecisionEngine Dependencies Troubleshooting Guide
**解决 DecisionEngine 服务依赖缺失问题**

---

## 🔍 问题诊断

### 症状

执行验证脚本时，在 Step 3（服务健康检查）失败，错误信息：

```
Invoke-WebRequest : 无法连接到远程服务器
```

查看 Docker 日志发现根本原因：

```
ModuleNotFoundError: No module named 'pandas'
```

### 根本原因分析

**问题**: Docker 镜像是在添加 ML/LLM 依赖之前构建的，容器中缺少以下依赖：

| 依赖包 | 版本 | 用途 | 添加时间 |
|--------|------|------|---------|
| `pandas` | 2.1.3 | 数据处理 | Phase 2 - Task 2.1 (ML引擎) |
| `pandas-ta` | 0.4.71b0 | 技术指标计算 | Phase 2 - Task 2.1 (ML引擎) |
| `scikit-learn` | 1.3.2 | 机器学习 | Phase 2 - Task 2.1 (ML引擎) |
| `xgboost` | 2.0.2 | 机器学习模型 | Phase 2 - Task 2.1 (ML引擎) |
| `numpy` | 1.26.2 | 数值计算 | Phase 2 - Task 2.1 (ML引擎) |
| `joblib` | 1.3.2 | 模型序列化 | Phase 2 - Task 2.1 (ML引擎) |
| `dashscope` | 1.14.0 | Qwen API客户端 | Phase 2 - Task 2.2 (LLM引擎) |
| `tenacity` | 8.2.3 | 重试机制 | Phase 2 - Task 2.2 (LLM引擎) |

**为什么会发生**:
1. Phase 1 完成时构建了 Docker 镜像
2. Phase 2 添加了 ML/LLM 依赖到 `requirements.txt`
3. 但没有重新构建 Docker 镜像
4. 容器启动时尝试导入新依赖，失败

**导入链**:
```
main.py
  → scheduler.py
    → rule_engine.py
      → feature_engineer.py
        → import pandas as pd  ← 失败点
```

---

## 🛠️ 解决方案

### 方案1: 完整重建（推荐，永久修复）

**优点**: 
- ✅ 永久修复，镜像包含所有依赖
- ✅ 适合生产环境
- ✅ 确保依赖版本一致

**缺点**:
- ⏱️ 需要 2-5 分钟

**执行步骤**:

```powershell
# 运行自动修复脚本
.\fix_decision_engine_dependencies.ps1
```

**或者手动执行**:

```powershell
# Step 1: 停止服务
docker-compose stop decision_engine

# Step 2: 重建镜像（不使用缓存）
docker-compose build --no-cache decision_engine

# Step 3: 启动服务
docker-compose up -d decision_engine

# Step 4: 等待服务启动
Start-Sleep -Seconds 15

# Step 5: 验证健康状态
Invoke-WebRequest -Uri "http://localhost:8002/health" -Method GET
```

---

### 方案2: 快速修复（临时方案）

**优点**:
- ⚡ 快速，1-2 分钟
- ✅ 立即可用

**缺点**:
- ⚠️ 临时修复，容器重建后会丢失
- ⚠️ 不适合生产环境

**执行步骤**:

```powershell
# 运行快速修复脚本
.\quick_fix_dependencies.ps1
```

**或者手动执行**:

```powershell
# Step 1: 在运行中的容器内安装依赖
docker-compose exec decision_engine pip install --no-cache-dir -r requirements.txt

# Step 2: 重启服务
docker-compose restart decision_engine

# Step 3: 等待服务启动
Start-Sleep -Seconds 10

# Step 4: 验证
docker-compose exec decision_engine python -c "import pandas; print(pandas.__version__)"
```

---

### 方案3: 手动安装单个依赖（调试用）

如果只想快速测试某个依赖：

```powershell
# 安装 pandas
docker-compose exec decision_engine pip install pandas==2.1.3

# 安装 dashscope
docker-compose exec decision_engine pip install dashscope==1.14.0

# 重启服务
docker-compose restart decision_engine
```

---

## ✅ 验证修复

### 1. 检查依赖是否安装

```powershell
# 检查所有 ML/LLM 依赖
docker-compose exec decision_engine pip list | Select-String -Pattern "pandas|scikit-learn|xgboost|dashscope|tenacity"
```

**预期输出**:
```
pandas                2.1.3
pandas-ta             0.4.71b0
scikit-learn          1.3.2
xgboost               2.0.2
dashscope             1.14.0
tenacity              8.2.3
```

### 2. 测试导入

```powershell
# 测试 pandas 导入
docker-compose exec decision_engine python -c "import pandas; print('pandas:', pandas.__version__)"

# 测试 pandas_ta 导入
docker-compose exec decision_engine python -c "import pandas_ta; print('pandas_ta:', pandas_ta.__version__)"

# 测试 sklearn 导入
docker-compose exec decision_engine python -c "import sklearn; print('sklearn:', sklearn.__version__)"

# 测试 xgboost 导入
docker-compose exec decision_engine python -c "import xgboost; print('xgboost:', xgboost.__version__)"

# 测试 dashscope 导入
docker-compose exec decision_engine python -c "import dashscope; print('dashscope:', dashscope.__version__)"

# 测试 tenacity 导入
docker-compose exec decision_engine python -c "import tenacity; print('tenacity:', tenacity.__version__)"
```

**预期输出**: 每个命令都应该打印版本号，无错误

### 3. 检查服务健康

```powershell
# 健康检查
Invoke-WebRequest -Uri "http://localhost:8002/health" -Method GET
```

**预期输出**: `StatusCode: 200`

### 4. 检查日志

```powershell
# 查看最近的日志
docker-compose logs decision_engine --tail=50
```

**预期输出**: 
- ✅ 看到 "Application startup complete"
- ✅ 看到 "ML adapter initialized successfully"
- ✅ 看到 "LLM adapter initialized successfully"
- ❌ 没有 "ModuleNotFoundError" 或 "ImportError"

### 5. 测试信号生成

```powershell
$body = @{ market = "BTCUSDT" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8002/v1/signals/generate" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

**预期输出**: JSON 响应包含 `ml_confidence_score` 和 `llm_sentiment` 字段

---

## 🔧 常见问题

### Q1: 重建镜像时出现 "no space left on device" 错误

**原因**: Docker 磁盘空间不足

**解决方法**:
```powershell
# 清理未使用的镜像和容器
docker system prune -a

# 查看磁盘使用情况
docker system df
```

---

### Q2: pip install 时出现网络超时

**原因**: 网络连接问题或 PyPI 服务器慢

**解决方法**:
```powershell
# 使用国内镜像源（阿里云）
docker-compose exec decision_engine pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 或使用清华镜像源
docker-compose exec decision_engine pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

---

### Q3: 重建后仍然缺少依赖

**原因**: Docker 使用了缓存的旧层

**解决方法**:
```powershell
# 强制重建，不使用缓存
docker-compose build --no-cache decision_engine

# 或者删除旧镜像后重建
docker rmi projectbedrock-decision_engine
docker-compose build decision_engine
```

---

### Q4: 容器启动后立即退出

**原因**: 可能是代码错误或配置问题

**排查步骤**:
```powershell
# 查看完整日志
docker-compose logs decision_engine

# 查看容器退出状态
docker-compose ps decision_engine

# 尝试手动运行容器查看详细错误
docker-compose run --rm decision_engine python -m uvicorn services.decision_engine.app.main:app --host 0.0.0.0 --port 8002
```

---

### Q5: 依赖版本冲突

**症状**: 安装依赖时出现版本冲突错误

**解决方法**:
```powershell
# 查看冲突详情
docker-compose exec decision_engine pip check

# 如果是 numpy 版本冲突（常见问题）
docker-compose exec decision_engine pip install numpy==1.26.2 --force-reinstall

# 重新安装所有依赖
docker-compose exec decision_engine pip install --no-cache-dir -r requirements.txt --force-reinstall
```

---

## 📋 完整修复检查清单

修复完成后，请确认以下所有项：

- [ ] Docker 镜像已重建（或依赖已安装）
- [ ] DecisionEngine 服务状态为 "Up"
- [ ] 健康检查返回 200 OK
- [ ] 所有 8 个 ML/LLM 依赖已安装
- [ ] 所有依赖可以成功导入（无 ImportError）
- [ ] 日志中看到 "ML adapter initialized successfully"
- [ ] 日志中看到 "LLM adapter initialized successfully"
- [ ] 信号生成 API 返回包含 `ml_confidence_score` 字段
- [ ] 信号生成 API 返回包含 `llm_sentiment` 字段
- [ ] 验证脚本 Step 3（健康检查）通过

---

## 🚀 修复后的下一步

修复完成后，继续执行验证流程：

```powershell
# 运行完整验证脚本
.\verify_llm_integration.ps1
```

**预期结果**:
- ✅ Step 1: 环境配置检查 - PASSED
- ✅ Step 2: 重启服务 - PASSED
- ✅ Step 3: 健康检查 - PASSED ← 之前失败的步骤
- ✅ Step 4: 信号生成测试 - PASSED
- ✅ Step 5: 日志检查 - PASSED
- ✅ Step 6: 单元测试 - PASSED (27/27)

---

## 📊 修复时间估算

| 方案 | 预计时间 | 适用场景 |
|------|---------|---------|
| 方案1: 完整重建 | 2-5 分钟 | 生产环境、永久修复 |
| 方案2: 快速修复 | 1-2 分钟 | 开发测试、临时修复 |
| 方案3: 手动安装 | 30 秒 | 调试单个依赖 |

---

## 🔒 预防措施

为避免将来再次出现此问题：

1. **每次修改 requirements.txt 后重建镜像**
   ```powershell
   docker-compose build decision_engine
   ```

2. **使用 CI/CD 自动化**
   - 在 CI 流程中自动检测 requirements.txt 变化
   - 自动触发镜像重建

3. **定期清理和重建**
   ```powershell
   # 每周执行一次
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

4. **版本锁定**
   - 确保 requirements.txt 中所有依赖都指定了版本号
   - 避免使用 `>=` 或 `~=` 等不确定版本

---

**如有其他问题，请查看项目文档或联系技术支持。**

