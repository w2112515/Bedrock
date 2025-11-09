# Project Bedrock Architecture Documentation

## System Overview

Project Bedrock is a microservices-based cryptocurrency trading decision platform that combines rule-based strategies, machine learning, and large language models to generate intelligent trading signals.

## Architecture Principles

### 1. Domain-Driven Design (DDD)

Each service represents a bounded context:
- **DataHub**: Data collection and storage domain
- **DecisionEngine**: Signal generation and decision-making domain
- **Portfolio**: Position and trade management domain
- **Backtesting**: Strategy evaluation domain
- **MLOps**: Model training and deployment domain
- **Notification**: Real-time communication domain

### 2. Microservices Architecture

**Benefits**:
- Independent deployment and scaling
- Technology diversity (Python for backend, React for frontend)
- Fault isolation
- Team autonomy

**Challenges**:
- Distributed system complexity
- Data consistency
- Service discovery and communication

### 3. Event-Driven Communication

Services communicate asynchronously via Redis Pub/Sub:

```
DataHub → signal.created → DecisionEngine
DecisionEngine → signal.created → PortfolioService
PortfolioService → portfolio.updated → NotificationService
```

**Benefits**:
- Loose coupling
- Scalability
- Resilience

### 4. Interface Segregation

All external dependencies are abstracted behind interfaces:
- `ExchangeInterface`: Binance, Bybit, etc.
- `MLModelInterface`: XGBoost, TensorFlow, etc.
- `LLMInterface`: Qwen, GPT, etc.
- `ChainDataInterface`: Bitquery, The Graph, etc.

**Benefits**:
- Easy to swap implementations
- Testability (mock interfaces)
- Vendor independence

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│                      http://localhost:3000                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/WebSocket
                            │
┌───────────────────────────┴─────────────────────────────────────┐
│                      API Gateway (Future)                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌──────▼───────┐  ┌───────▼────────┐
│  DataHub       │  │  Decision    │  │  Portfolio     │
│  Service       │  │  Engine      │  │  Service       │
│  :8001         │  │  Service     │  │  :8003         │
│                │  │  :8002       │  │                │
│ - K-line data  │  │ - Rule Eng.  │  │ - Positions    │
│ - Chain data   │  │ - ML Model   │  │ - Trades       │
│                │  │ - LLM        │  │ - Risk Mgmt    │
└────────┬───────┘  └──────┬───────┘  └───────┬────────┘
         │                 │                   │
         │                 │                   │
┌────────▼─────────────────▼───────────────────▼────────┐
│                  Redis Pub/Sub                         │
│              (Event Bus + Cache)                       │
└────────────────────────────┬───────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
│  Backtesting   │  │  MLOps         │  │  Notification  │
│  Service       │  │  Service       │  │  Service       │
│  :8004         │  │  :8005         │  │  :8006         │
│                │  │                │  │                │
│ - Backtest     │  │ - Training     │  │ - WebSocket    │
│ - Reports      │  │ - Registry     │  │ - Push         │
└────────┬───────┘  └───────┬────────┘  └───────┬────────┘
         │                  │                    │
         └──────────────────┼────────────────────┘
                            │
                ┌───────────▼───────────┐
                │   PostgreSQL          │
                │   (Shared Database)   │
                └───────────────────────┘
```

## Data Flow

### 1. Signal Generation Flow

```
1. DataHub collects K-line data from Binance
2. DataHub stores data in PostgreSQL
3. DecisionEngine queries K-line data
4. DecisionEngine runs Rule Engine
5. DecisionEngine calls ML Model
6. DecisionEngine calls LLM for sentiment
7. DecisionEngine performs arbitration
8. DecisionEngine creates Signal in database
9. DecisionEngine publishes "signal.created" event to Redis
10. PortfolioService receives event
11. PortfolioService creates Position
12. PortfolioService publishes "portfolio.updated" event
13. NotificationService receives event
14. NotificationService pushes update to frontend via WebSocket
```

### 2. Position Management Flow

```
1. User views signals in frontend
2. User clicks "Estimate" button
3. Frontend calls PortfolioService API
4. PortfolioService calculates position size
5. PortfolioService returns estimation
6. User confirms
7. PortfolioService creates Position
8. PortfolioService publishes event
9. Frontend receives real-time update
```

## Database Design

### Centralized Database Strategy

All services share a single PostgreSQL database with centralized migration management.

**Rationale**:
- Simplifies data consistency
- Reduces operational complexity
- Suitable for MVP phase

**Trade-offs**:
- Tight coupling at data layer
- Potential scaling bottleneck (mitigated by read replicas)

### Table Ownership

Each table is owned by one service (see DATABASE_MIGRATION_COORDINATION.md).

### Key Tables

- `klines`: K-line data (DataHub)
- `chain_data`: On-chain data (DataHub)
- `signals`: Trading signals (DecisionEngine)
- `positions`: Open positions (Portfolio)
- `trades`: Trade history (Portfolio)
- `backtest_tasks`: Backtest tasks (Backtesting)
- `backtest_reports`: Backtest reports (Backtesting)
- `training_jobs`: ML training jobs (MLOps)
- `ml_models`: ML model metadata (MLOps)

## Technology Choices

### Backend: FastAPI + SQLAlchemy

**Rationale**:
- High performance (async support)
- Automatic API documentation (OpenAPI)
- Type safety (Pydantic)
- Mature ORM (SQLAlchemy)

### Frontend: React + TypeScript

**Rationale**:
- Component-based architecture
- Large ecosystem
- Type safety
- Developer experience

### Database: PostgreSQL

**Rationale**:
- ACID compliance
- JSON support (JSONB)
- Mature and reliable
- Rich indexing options

### Cache/Message Broker: Redis

**Rationale**:
- High performance
- Pub/Sub support
- Simple to operate
- Versatile (cache + message broker)

### Containerization: Docker + Kubernetes

**Rationale**:
- Consistent environments
- Easy deployment
- Scalability
- Industry standard

## Security Considerations

### API Security

- API key authentication for external APIs
- Rate limiting
- Input validation (Pydantic)
- SQL injection prevention (SQLAlchemy ORM)

### Data Security

- Encrypted connections (TLS)
- Sensitive data encryption at rest
- Environment variable management
- Secrets management (Kubernetes Secrets)

### Network Security

- Service-to-service authentication (future)
- Network policies (Kubernetes)
- Firewall rules

## Scalability Strategy

### Horizontal Scaling

- Stateless services (easy to scale)
- Load balancing (Kubernetes)
- Database read replicas

### Vertical Scaling

- Resource limits (CPU, memory)
- Auto-scaling (HPA)

### Caching Strategy

- Redis caching for frequently accessed data
- Cache invalidation on updates

## Monitoring and Observability

### Metrics (Prometheus)

- Request rate, latency, error rate
- Database connection pool
- Redis connection pool
- Business metrics (signals generated, positions opened)

### Logging (Structlog)

- Structured JSON logs
- Centralized logging (future: ELK stack)
- Log levels (DEBUG, INFO, WARNING, ERROR)

### Tracing (Future)

- Distributed tracing (Jaeger)
- Request correlation IDs

## Deployment Strategy

### Development

- Docker Compose
- Local PostgreSQL and Redis

### Staging

- Kubernetes cluster
- Separate namespace
- Production-like configuration

### Production

- Kubernetes cluster
- High availability (multiple replicas)
- Automated backups
- Blue-green deployment

## Future Enhancements

1. **API Gateway**: Centralized routing, authentication, rate limiting
2. **Service Mesh**: Istio for advanced traffic management
3. **CQRS**: Separate read and write models for better scalability
4. **Event Sourcing**: Store all state changes as events
5. **GraphQL**: Flexible data querying for frontend
6. **Multi-Region**: Deploy to multiple regions for lower latency

## References

- [Microservices Patterns](https://microservices.io/patterns/)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [Twelve-Factor App](https://12factor.net/)

---

**Last Updated**: 2025-11-09

