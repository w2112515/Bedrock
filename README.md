# Bedrock: AI 增强型加密货币交易决策平台
# AI-Enhanced Cryptocurrency Trading Decision Platform

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18.2.0-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)](https://fastapi.tiangolo.com/)

---

## 📖 项目简介 (Project Overview)

Bedrock 是一个**从零到一、完全通过自然语言指令驱动 AI 构建**的专业级量化交易平台原型。本项目旨在验证在无编程背景下，通过高效的**人机协作（AI Native Workflow）**完成复杂软件工程的可行性。

**作为项目发起人和唯一的 AI 产品设计师，我独立负责了从产品规划、架构设计、任务拆解到驱动 AI 开发的全过程。**

> **💼 求职备注**: 此仓库不仅是软件代码的集合，更是我作为一名准产品人，在**复杂问题拆解、产品架构设计、AI 原生工作流管理**等核心能力上的实践案例。欢迎通过此项目了解我的工作方法和交付质量。

---

## 🎯 项目核心价值 (Core Value)

### 能力验证 (Capability Validation)
- ✅ **产品思维**: 将模糊的商业构想转化为清晰、可执行的技术蓝图
- ✅ **架构设计**: 主导设计了包含 6 个微服务的分布式系统架构
- ✅ **任务拆解**: 将复杂项目拆解为 100+ 个可执行的开发任务
- ✅ **AI 协作**: 探索并实践了一套完整的 AI 原生工作流，成功驱动 AI 完成核心功能开发

### 成果交付 (Deliverables)
- 📊 **20+ 份专业技术文档**: 包括 PRD、系统架构、API 契约、数据库设计等
- 💻 **可运行的软件原型**: 包含前后端、数据库、ML 模型的完整系统
- 🏗️ **微服务架构**: 6 个独立服务，事件驱动通信，容器化部署
- 🤖 **AI 集成**: Rule Engine + XGBoost ML + Qwen LLM 三层决策系统

### 技术亮点 (Technical Highlights)
- 🎨 **微服务架构**: DataHub、DecisionEngine、Portfolio、Backtesting、MLOps、Notification
- 🧠 **三层决策系统**: 规则引擎（技术指标）+ ML 模型（XGBoost 94.33% 准确率）+ LLM 情绪分析（Qwen）
- 📈 **实时数据处理**: Binance K线数据 + Bitquery 链上数据
- 🔄 **事件驱动架构**: Redis Pub/Sub 实现服务间异步通信
- 🐳 **容器化部署**: Docker Compose 本地开发，Kubernetes 生产部署
- 📊 **可观测性**: Prometheus 监控 + 结构化日志 + 健康检查

---

## 🗺️ 导航：如何浏览本项目？ (How to Navigate This Repository)

为了方便您快速了解我的工作成果，建议按以下顺序查看关键交付物：

### 1️⃣ 产品与架构设计
- **[项目计划书 (Project Plan)](./2.md)** ⭐ 核心文档
  - 查看完整的产品愿景、架构原则、功能规划
  - 了解我如何将商业需求转化为技术方案

- **[系统架构图 (System Architecture)](./2.md#21-高阶系统架构图文字描述)**
  - 查看我主导设计的微服务架构和数据流
  - 理解服务间的交互模式和技术选型

### 2️⃣ 技术实现
- **[数据库迁移脚本 (Database Migrations)](./database_migrations/alembic/versions/)**
  - 查看 8 个 Alembic 迁移脚本，了解数据库演进过程
  - 核心表：`klines`、`onchain_metrics`、`signals`、`positions`、`trades`、`backtest_runs`

- **[API 实现 (API Implementation)](./services/)**
  - **DataHub Service**: 数据采集与存储 ([代码](./services/datahub/))
  - **DecisionEngine Service**: 信号生成与决策仲裁 ([代码](./services/decision_engine/))
  - **Portfolio Service**: 仓位与交易管理 ([代码](./services/portfolio/))
  - **Backtesting Service**: 策略回测引擎 ([代码](./services/backtesting/))

- **[前端应用 (Frontend App)](./webapp/)**
  - React + TypeScript + Ant Design 5
  - 包含 Dashboard、Signals、Positions、Trades、Backtest 页面

### 3️⃣ AI 协作工作流
- **[AI 指令任务拆解示例](./2.md#第三部分功能点详细设计-the-what)**
  - 查看我如何将复杂需求拆解为 AI 可理解的具体指令
  - 了解我的 Prompt Engineering 能力

- **[技术文档 (Technical Docs)](./docs/)**
  - Funding Rate 策略文档
  - ML 模型特征工程文档
  - 依赖问题排查指南

---

## 🛠️ 技术栈与工具 (Tech Stack & Tools)

### AI 模型 (AI Models)
- **LLM**: Alibaba Cloud Qwen (通义千问) - 市场情绪分析
- **ML**: XGBoost 2.1.4 - 信号预测（94.33% 准确率）
- **协作工具**: Claude 3.5 Sonnet, GPT-4 - AI 驱动开发

### 后端技术栈 (Backend)
- **语言**: Python 3.12.12
- **框架**: FastAPI 0.104.1 (异步 Web 框架)
- **ORM**: SQLAlchemy 2.0.23 (数据库 ORM)
- **数据库**: PostgreSQL 16 (主数据库) + Redis 7 (缓存 & Pub/Sub)
- **ML 库**: XGBoost 2.1.4, scikit-learn 1.5.2, numpy 2.2.6, pandas 2.3.2
- **迁移工具**: Alembic (数据库版本管理)

### 前端技术栈 (Frontend)
- **框架**: React 18.2.0 + TypeScript 5.x
- **UI 库**: Ant Design 5.11.0
- **状态管理**: React Query v5 (@tanstack/react-query)
- **图表库**: ECharts (K线图、性能图表)
- **构建工具**: Vite 5.x

### 基础设施 (Infrastructure)
- **容器化**: Docker 20.10+, Docker Compose 2.0+
- **编排**: Kubernetes (生产环境)
- **监控**: Prometheus + Grafana
- **日志**: 结构化日志 (JSON 格式)
- **CI/CD**: GitHub Actions (计划中)

### 外部 API (External APIs)
- **交易所**: Binance API (K线数据、资金费率)
- **链上数据**: Bitquery API (链上指标)
- **LLM**: Alibaba Cloud Qwen API (dashscope 1.14.0)

---

## 🏗️ 系统架构 (System Architecture)

### 微服务架构 (Microservices Architecture)

本项目采用**事件驱动的微服务架构**，6 个独立服务通过 Redis Pub/Sub 进行异步通信：

| 服务名称 | 端口 | 职责 | 技术栈 |
|---------|------|------|--------|
| **DataHub** | 8001 | 数据采集与存储 | FastAPI + Binance API + Bitquery API |
| **DecisionEngine** | 8002 | 信号生成与决策仲裁 | FastAPI + XGBoost + Qwen LLM |
| **Portfolio** | 8003 | 仓位与交易管理 | FastAPI + SQLAlchemy |
| **Backtesting** | 8004 | 策略回测引擎 | FastAPI + Pandas |
| **MLOps** | 8005 | 模型训练与管理 | FastAPI + Celery + XGBoost |
| **Notification** | 8006 | 实时 WebSocket 推送 | FastAPI + WebSocket |

### 事件驱动通信 (Event-Driven Communication)

服务间通过 **Redis Pub/Sub** 进行异步通信，实现松耦合：

```
DataHub → [kline.updated] → DecisionEngine
DecisionEngine → [signal.created] → Portfolio
Portfolio → [position.updated] → Notification → WebApp
```

### 三层决策系统 (Three-Layer Decision System)

```
┌─────────────────────────────────────────────────────────┐
│                    DecisionEngine                        │
├─────────────────────────────────────────────────────────┤
│  1️⃣ Rule Engine (规则引擎)                              │
│     - 技术指标: RSI, MACD, Bollinger Bands              │
│     - 链上指标: Active Addresses, Transaction Volume    │
│     - 输出: rule_score (0-100)                          │
├─────────────────────────────────────────────────────────┤
│  2️⃣ ML Model (机器学习模型)                             │
│     - XGBoost 分类器 (94.33% 准确率)                    │
│     - 特征工程: 60+ 技术指标 + 链上指标                  │
│     - 输出: ml_confidence_score (0-100)                 │
├─────────────────────────────────────────────────────────┤
│  3️⃣ LLM Sentiment (大语言模型情绪分析)                   │
│     - Qwen API 市场情绪分析                             │
│     - Redis 缓存 (15分钟 TTL)                           │
│     - 输出: llm_sentiment_score (0-100)                 │
├─────────────────────────────────────────────────────────┤
│  🎯 Decision Arbiter (决策仲裁器)                        │
│     - 加权融合: Rule 40% + ML 30% + LLM 30%            │
│     - 输出: final_score (0-100) + 交易信号              │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 项目状态 (Project Status)

### 开发阶段 (Development Phases)

| 阶段 | 状态 | 完成度 | 关键成果 |
|------|------|--------|----------|
| **Phase 0: 环境搭建** | ✅ 已完成 | 100% | Docker 环境、数据库设计、共享库 |
| **Phase 1: MVP 开发** | ✅ 已完成 | 100% | DataHub、DecisionEngine、Portfolio 服务 |
| **Phase 2: AI 集成** | ✅ 已完成 | 100% | XGBoost ML 模型、Qwen LLM、决策仲裁器 |
| **Phase 3: 回测与优化** | 🚧 进行中 | 60% | 回测引擎、前端增强、性能优化 |
| **Phase 4: 生产就绪** | ⏸️ 计划中 | 0% | MLOps 自动化、Kubernetes 部署、CI/CD |

### 核心功能完成情况 (Feature Completion)

- ✅ **数据采集**: Binance K线数据 + Bitquery 链上数据
- ✅ **规则引擎**: 技术指标计算 + 链上指标分析
- ✅ **ML 模型**: XGBoost 训练与预测（94.33% 准确率）
- ✅ **LLM 集成**: Qwen API 情绪分析 + Redis 缓存
- ✅ **决策仲裁**: 三层加权融合（Rule + ML + LLM）
- ✅ **仓位管理**: 建仓、平仓、止损、止盈逻辑
- ✅ **前端界面**: Dashboard、Signals、Positions、Trades 页面
- 🚧 **回测引擎**: 基础框架完成，性能优化中
- ⏸️ **实时推送**: WebSocket 通知服务（计划中）
- ⏸️ **MLOps**: 模型自动训练与部署（计划中）

### 最近更新 (Recent Updates)

- **2025-11-17**: ✅ 完成 LLM 情绪分数回填（22 条历史信号）
- **2025-11-16**: ✅ 实现决策仲裁器权重配置（Rule 40% + ML 30% + LLM 30%）
- **2025-11-12**: ✅ 集成 Qwen LLM API + Redis 缓存
- **2025-11-11**: ✅ XGBoost 模型训练完成（94.33% 准确率）
- **2025-11-10**: ✅ 数据库迁移脚本完成（8 个 Alembic 版本）

---

## 🚀 快速开始 (Quick Start)

### 前置要求 (Prerequisites)

- **Docker** 20.10+ 和 **Docker Compose** 2.0+
- **Python** 3.12+ (用于本地开发和脚本)
- **Node.js** 18+ (用于前端开发)
- **Git** 2.x+

### 安装步骤 (Installation)

#### 1️⃣ 克隆仓库
```bash
git clone https://github.com/w2112515/Bedrock.git
cd Bedrock
```

#### 2️⃣ 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，填入以下 API 密钥：
# - BINANCE_API_KEY 和 BINANCE_API_SECRET (Binance API)
# - BITQUERY_API_KEY (Bitquery API)
# - QWEN_API_KEY (Alibaba Cloud Qwen API)
# - POSTGRES_PASSWORD (数据库密码)
```

#### 3️⃣ 启动基础设施服务
```bash
docker-compose up -d postgres redis
```

#### 4️⃣ 运行数据库迁移
```bash
cd database_migrations
pip install alembic psycopg2-binary
alembic upgrade head
```

#### 5️⃣ 启动所有微服务
```bash
docker-compose up -d
```

#### 6️⃣ 访问应用
- **前端界面**: http://localhost:3000
- **API 文档**:
  - DataHub: http://localhost:8001/docs
  - DecisionEngine: http://localhost:8002/docs
  - Portfolio: http://localhost:8003/docs
  - Backtesting: http://localhost:8004/docs

### 验证安装 (Verify Installation)

```bash
# 检查服务健康状态
curl http://localhost:8001/health  # DataHub
curl http://localhost:8002/health  # DecisionEngine
curl http://localhost:8003/health  # Portfolio

# 查看数据库表
docker exec -it bedrock_postgres psql -U bedrock_user -d bedrock_db -c "\dt"

# 查看 Redis 连接
docker exec -it bedrock_redis redis-cli ping
```

---

## 📚 核心文档 (Core Documentation)

### 产品与架构文档 (Product & Architecture)
- **[项目计划书 v2.0](./2.md)** ⭐ 核心文档 - 完整的产品愿景、架构原则、功能规划
- **[Funding Rate 策略文档](./docs/FUNDING_RATE_STRATEGY.md)** - 资金费率策略设计
- **[ML 模型特征工程](./docs/ML_MODEL_FEATURES.md)** - 机器学习模型特征说明

### 技术文档 (Technical Docs)
- **[依赖问题排查指南](./TROUBLESHOOTING_DEPENDENCIES.md)** - Python 3.12 升级指南
- **[数据库迁移脚本](./database_migrations/alembic/versions/)** - 8 个 Alembic 迁移版本
- **[DecisionEngine 实现总结](./services/decision_engine/IMPLEMENTATION_SUMMARY.md)** - 决策引擎实现细节

### 服务文档 (Service Docs)
- **[DataHub 测试总结](./services/datahub/tests/FINAL_TEST_SUMMARY.md)** - 数据服务测试报告
- **[模型部署指南](./services/decision_engine/docs/MODEL_DEPLOYMENT_GUIDE.md)** - ML 模型部署流程
- **[稳定性验证指南](./services/decision_engine/docs/stability_validation_implementation.md)** - 模型稳定性验证

---

## 🧪 测试 (Testing)

### 单元测试 (Unit Tests)

```bash
# 后端服务测试
pytest services/datahub/tests/ -v
pytest services/decision_engine/tests/ -v
pytest services/portfolio/tests/ -v
pytest services/backtesting/tests/ -v

# 前端测试
cd webapp
npm test
```

### 集成测试 (Integration Tests)

```bash
# 测试完整的信号生成流程
python scripts/create_test_signal_with_ml_llm.py

# 验证数据一致性
python services/decision_engine/scripts/verify_data_consistency.py

# 验证模型确定性
python services/decision_engine/scripts/verify_determinism.py
```

### 性能测试 (Performance Tests)

```bash
# 使用 Locust 进行负载测试
locust -f tests/performance/locustfile.py --host=http://localhost:8001
```

---

## 💡 核心功能演示 (Feature Showcase)

### 1️⃣ 信号生成流程 (Signal Generation Flow)

```python
# 1. DataHub 采集数据
GET /api/klines?symbol=BTCUSDT&interval=4h&limit=100

# 2. DecisionEngine 生成信号
POST /api/signals/generate
{
  "symbol": "BTCUSDT",
  "interval": "4h"
}

# 响应示例
{
  "signal_id": "uuid-xxx",
  "symbol": "BTCUSDT",
  "direction": "LONG",
  "rule_score": 75.5,           # 规则引擎分数
  "ml_confidence_score": 88.2,  # ML 模型置信度
  "llm_sentiment_score": 82.0,  # LLM 情绪分数
  "final_score": 81.9,          # 加权最终分数
  "entry_price": 45000.0,
  "stop_loss": 44000.0,
  "take_profit": 47000.0
}
```

### 2️⃣ 决策仲裁器配置 (Arbiter Configuration)

```python
# 查看当前权重配置
GET /api/arbitration/config

# 响应
{
  "rule_weight": 0.4,   # 规则引擎权重 40%
  "ml_weight": 0.3,     # ML 模型权重 30%
  "llm_weight": 0.3     # LLM 权重 30%
}

# 更新权重配置
PUT /api/arbitration/config
{
  "rule_weight": 0.5,
  "ml_weight": 0.3,
  "llm_weight": 0.2
}
```

### 3️⃣ 仓位管理 (Position Management)

```python
# 查看当前仓位
GET /api/positions?status=OPEN

# 响应
[
  {
    "position_id": "uuid-xxx",
    "symbol": "BTCUSDT",
    "direction": "LONG",
    "entry_price": 45000.0,
    "current_price": 46000.0,
    "quantity": 0.1,
    "unrealized_pnl": 100.0,
    "unrealized_pnl_pct": 2.22
  }
]
```

---

## 🎓 我的工作方法 (My Workflow)

### AI 原生工作流 (AI Native Workflow)

作为项目的唯一产品设计师，我开发了一套高效的 AI 协作工作流：

#### 1️⃣ 需求分析与拆解 (Requirement Analysis)
- 将模糊的商业需求转化为清晰的功能点
- 使用 Mermaid 图表可视化系统架构和数据流
- 编写详细的 PRD 和技术规格文档

#### 2️⃣ 任务拆解与 Prompt Engineering
- 将复杂功能拆解为 100+ 个可执行的开发任务
- 为每个任务编写清晰、具体的 AI 指令
- 使用三阶段工作流：分析与诊断 → 方案设计 → 执行与验证

#### 3️⃣ AI 驱动开发 (AI-Driven Development)
- 使用 Claude 3.5 Sonnet 和 GPT-4 进行代码生成
- 通过迭代式对话优化代码质量
- 确保代码符合架构原则和最佳实践

#### 4️⃣ 质量保证与文档 (Quality Assurance)
- 编写单元测试和集成测试
- 生成 API 文档和技术文档
- 进行代码审查和性能优化

### 关键成果 (Key Achievements)

- ✅ **100% AI 驱动开发**: 所有代码由 AI 生成，我负责需求定义和质量把控
- ✅ **20+ 份专业文档**: 包括 PRD、架构设计、API 契约、数据库设计等
- ✅ **284 个文件，43,948 行代码**: 完整的前后端系统
- ✅ **8 个数据库迁移脚本**: 规范的数据库版本管理
- ✅ **94.33% ML 模型准确率**: 高质量的机器学习模型
- ✅ **微服务架构**: 6 个独立服务，事件驱动通信

---

## 📝 许可证 (License)

本项目采用 **GPL v3** (GNU General Public License v3.0) 许可证。

- **版权所有者**: Zian Wang
- **版权年份**: 2025
- **许可证详情**: 查看 [LICENSE](./LICENSE) 文件

**注意**: GPL v3 要求所有衍生作品也必须开源。

---

## 📧 联系方式 (Contact)

### 项目作者 (Project Author)
- **姓名**: Zian Wang (王子安)
- **GitHub**: [@w2112515](https://github.com/w2112515)
- **项目仓库**: [Bedrock](https://github.com/w2112515/Bedrock)

### 求职意向 (Job Seeking)
我正在寻找**产品经理**、**AI 产品经理**或**技术产品经理**相关职位。

**核心能力**:
- ✅ 复杂问题拆解与需求分析
- ✅ 产品架构设计与技术选型
- ✅ AI 原生工作流管理
- ✅ 跨职能团队协作（人机协作）
- ✅ 技术文档撰写与沟通

**如果您对我的工作感兴趣，欢迎通过 GitHub Issues 或 Email 联系我。**

---

## 🙏 致谢 (Acknowledgments)

### 技术支持 (Technical Support)
- **Binance API** - 提供实时市场数据和资金费率数据
- **Bitquery API** - 提供链上数据和区块链分析
- **Alibaba Cloud Qwen** - 提供大语言模型 API 服务
- **Claude 3.5 Sonnet & GPT-4** - AI 驱动开发的核心工具

### 开源社区 (Open Source Community)
- **FastAPI** - 高性能异步 Web 框架
- **React & Ant Design** - 优秀的前端框架和 UI 库
- **XGBoost & scikit-learn** - 强大的机器学习库
- **PostgreSQL & Redis** - 可靠的数据库和缓存系统
- **Docker & Kubernetes** - 容器化和编排工具

---

## 📊 项目统计 (Project Statistics)

- **开发周期**: 2025-11-09 至今（约 8 天）
- **代码行数**: 43,948 行
- **文件数量**: 284 个
- **提交次数**: 1 次（初始提交）
- **服务数量**: 6 个微服务
- **数据库表**: 10+ 个核心业务表
- **API 端点**: 50+ 个 RESTful API
- **前端页面**: 5 个主要页面（Dashboard、Signals、Positions、Trades、Backtest）

---

## 🚀 未来规划 (Future Roadmap)

### 短期目标 (Short-term Goals)
- [ ] 完成回测引擎性能优化
- [ ] 实现 WebSocket 实时推送
- [ ] 添加更多技术指标和策略
- [ ] 完善前端 UI/UX

### 中期目标 (Mid-term Goals)
- [ ] MLOps 自动化（模型自动训练与部署）
- [ ] Kubernetes 生产环境部署
- [ ] CI/CD 流水线（GitHub Actions）
- [ ] 多交易所支持（OKX、Bybit）

### 长期目标 (Long-term Goals)
- [ ] 社区版本发布
- [ ] 插件系统（自定义策略）
- [ ] 移动端应用（React Native）
- [ ] 量化策略市场

---

**⭐ 如果您觉得这个项目有价值，欢迎 Star 支持！**

**📌 最后更新**: 2025-11-17

**🏷️ 项目标签**: `python` `fastapi` `react` `typescript` `xgboost` `llm` `cryptocurrency` `trading` `microservices` `ai-driven-development`
