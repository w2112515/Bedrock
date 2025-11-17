# Project Bedrock

## AI-Enhanced Cryptocurrency Trading Decision Platform

Project Bedrock is an intelligent cryptocurrency trading decision platform that combines rule-based strategies, machine learning models, and large language models (LLMs) to generate high-quality trading signals and manage positions effectively.

## 🎯 Project Overview

### Core Features

1. **Market Screening Module**: Filter trading opportunities using on-chain data and technical indicators
2. **Trade Plan Generation**: Generate entry/exit strategies with pullback buying and "Oops!" signals
3. **Position Management**: Intelligent position sizing using suggested weight system (Plan A)
4. **Strategy Education & Psychology**: Educational tips and psychological support for traders

### Technology Stack

- **Backend**: Python **3.12.12** ⭐, FastAPI 0.104.1, SQLAlchemy 2.0.23
- **Database**: PostgreSQL 16, Redis 7
- **Frontend**: React 18.2.0, TypeScript, Ant Design 5.11.0
- **ML/AI**:
  - XGBoost **2.1.4** ⭐
  - scikit-learn **1.5.2** ⭐
  - numpy **2.2.6** ⭐
  - pandas **2.3.2** ⭐
  - pandas-ta 0.4.71b0
  - Qwen LLM API (dashscope 1.14.0)
- **Infrastructure**: Docker, Docker Compose, Kubernetes
- **Monitoring**: Prometheus, Grafana

**⭐ Updated**: 2025-11-12 - Upgraded to Python 3.12 and numpy 2.x compatible ML stack

## 🏗️ Architecture

### Microservices

1. **DataHubService** (Port 8001): K-line data + on-chain data collection
2. **DecisionEngineService** (Port 8002): Signal generation (Rule Engine + ML + LLM)
3. **PortfolioService** (Port 8003): Position and trade management
4. **BacktestingService** (Port 8004): Strategy backtesting
5. **MLOpsService** (Port 8005): Model training and management
6. **NotificationService** (Port 8006): Real-time WebSocket notifications

### Event-Driven Architecture

Services communicate via Redis Pub/Sub:
- `signal.created` → PortfolioService creates positions
- `portfolio.updated` → NotificationService pushes updates to frontend

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Python **3.12+** ⭐
- Node.js 18+
- Git 2.x+

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd projectBedrock
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and fill in API keys
   ```

3. **Start infrastructure services**
   ```bash
   docker-compose up -d postgres redis
   ```

4. **Run database migrations**
   ```bash
   cd database_migrations
   alembic upgrade head
   ```

5. **Start all services**
   ```bash
   docker-compose up -d
   ```

6. **Access the application**
   - Frontend: http://localhost:3000
   - API Documentation: http://localhost:8001/docs (DataHub), http://localhost:8002/docs (DecisionEngine), etc.

## 📚 Documentation

- [Architecture Documentation](docs/ARCHITECTURE.md)
- [API Documentation](docs/API_DOCUMENTATION.md)
- [Data Model & API Contract](docs/DATA_MODEL_AND_API_CONTRACT.md)
- [Database Migration Coordination](docs/DATABASE_MIGRATION_COORDINATION.md)
- [Environment Variables](docs/ENVIRONMENT_VARIABLES.md)
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [Operations Guide](docs/OPERATIONS_GUIDE.md)

## 🧪 Testing

### Run Unit Tests

```bash
# Backend tests
pytest services/datahub/tests/
pytest services/decision_engine/tests/
pytest services/portfolio/tests/

# Frontend tests
cd webapp
npm test
```

### Run E2E Tests

```bash
cd webapp
npx playwright test
```

### Run Performance Tests

```bash
locust -f tests/performance/locustfile.py --host=http://localhost:8001
```

## 📊 Development Phases

### Phase 0: Environment Setup (1-2 weeks) ✅
- Infrastructure setup
- Shared libraries
- Documentation

### Phase 1: MVP Development (4-6 weeks) ✅
- DataHub, DecisionEngine, Portfolio services (100% complete)
- Basic frontend (90% complete)
- Rule-based signal generation (100% complete)
- Event-driven architecture (Redis Pub/Sub)

### Phase 2: AI Integration (6-8 weeks) ⏳ 40% Complete
- ✅ ML model integration (XGBoost, 94.33% accuracy) - **Completed 2025-11-11**
- ✅ LLM sentiment analysis (Qwen API, Redis cache) - **Completed 2025-11-12**
- ✅ Python 3.12 + numpy 2.x dependency upgrade - **Completed 2025-11-12**
- ⏳ Decision arbitration (Rule + ML + LLM fusion) - **In Progress**
- ⏸️ Backtesting engine - **Pending**
- ⏸️ Frontend enhancements - **Pending**

### Phase 3: Production Readiness (5-7 weeks)
- MLOps automation
- WebSocket notifications
- Kubernetes deployment
- CI/CD pipeline

### Phase 4: Platform Extensions (Ongoing)
- Multi-exchange support
- Advanced visualizations
- Security hardening

## 🤝 Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📧 Contact

For questions or support, please contact the development team.

## 🙏 Acknowledgments

- Binance API for market data
- Bitquery for on-chain data
- Qwen LLM for sentiment analysis
- Open-source community for amazing tools and libraries

---

**Project Status**: Phase 0 - Environment Setup ✅ | Phase 1 - MVP Development 🚧

**Last Updated**: 2025-11-09

