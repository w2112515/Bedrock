# Testing Strategy

## Overview

This document defines the testing strategy for Project Bedrock, including unit tests, integration tests, E2E tests, and performance tests.

## Testing Pyramid

```
        /\
       /  \
      / E2E \
     /--------\
    /          \
   / Integration\
  /--------------\
 /                \
/   Unit Tests     \
--------------------
```

## Test Coverage Goals

- **Unit Tests**: >70% code coverage
- **Integration Tests**: All service interactions
- **E2E Tests**: All critical user flows
- **Performance Tests**: All API endpoints

## Unit Tests

### Backend (Python)

**Framework**: pytest

**Location**: `services/{service_name}/tests/`

**Naming Convention**: `test_{module_name}.py`

**Example**:
```python
# services/portfolio/tests/test_position_sizing.py
import pytest
from services.portfolio.app.services.position_sizing import calculate_position_size

def test_calculate_position_size_basic():
    account_balance = 10000.0
    risk_percentage = 0.02
    stop_loss_distance = 0.05
    
    result = calculate_position_size(account_balance, risk_percentage, stop_loss_distance)
    
    assert result == 4000.0

def test_calculate_position_size_zero_stop_loss():
    with pytest.raises(ValueError):
        calculate_position_size(10000.0, 0.02, 0.0)
```

**Run Tests**:
```bash
pytest services/portfolio/tests/ -v --cov=services/portfolio
```

### Frontend (TypeScript)

**Framework**: Jest + React Testing Library

**Location**: `webapp/src/components/__tests__/`

**Naming Convention**: `{ComponentName}.test.tsx`

**Example**:
```typescript
// webapp/src/components/__tests__/SignalCard.test.tsx
import { render, screen } from '@testing-library/react';
import SignalCard from '../SignalCard';

describe('SignalCard', () => {
  it('renders signal information', () => {
    const signal = {
      id: 1,
      market: 'BTCUSDT',
      signal_type: 'PULLBACK_BUY',
      entry_price: 35000.0,
    };
    
    render(<SignalCard signal={signal} />);
    
    expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
    expect(screen.getByText('PULLBACK_BUY')).toBeInTheDocument();
  });
});
```

**Run Tests**:
```bash
cd webapp
npm test
```

## Integration Tests

### Service-to-Service Tests

**Framework**: pytest with test database

**Location**: `tests/integration/`

**Example**:
```python
# tests/integration/test_signal_to_position_flow.py
import pytest
from services.decision_engine.app.services.signal_generator import generate_signal
from services.portfolio.app.services.position_manager import create_position_from_signal

@pytest.mark.integration
def test_signal_to_position_flow(test_db):
    # Generate signal
    signal = generate_signal(market="BTCUSDT", interval="1h")
    assert signal.id is not None
    
    # Create position from signal
    position = create_position_from_signal(signal.id)
    assert position.signal_id == signal.id
    assert position.status == "OPEN"
```

**Run Tests**:
```bash
pytest tests/integration/ -v -m integration
```

### Database Tests

**Framework**: pytest with test database

**Setup**: Use separate test database

**Teardown**: Clean up test data after each test

## E2E Tests

### Frontend E2E Tests

**Framework**: Playwright

**Location**: `webapp/tests/e2e/`

**Example**:
```typescript
// webapp/tests/e2e/signal-flow.spec.ts
import { test, expect } from '@playwright/test';

test('user can view and create position from signal', async ({ page }) => {
  // Navigate to signals page
  await page.goto('http://localhost:3000/signals');
  
  // Wait for signals to load
  await page.waitForSelector('.signal-card');
  
  // Click first signal
  await page.click('.signal-card:first-child');
  
  // Click estimate button
  await page.click('button:has-text("Estimate")');
  
  // Verify estimation modal appears
  await expect(page.locator('.estimation-modal')).toBeVisible();
  
  // Confirm position creation
  await page.click('button:has-text("Confirm")');
  
  // Verify success message
  await expect(page.locator('.success-message')).toBeVisible();
});
```

**Run Tests**:
```bash
cd webapp
npx playwright test
```

## Performance Tests

### Load Testing

**Framework**: Locust

**Location**: `tests/performance/`

**Example**:
```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between

class BedrockUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def get_signals(self):
        self.client.get("/v1/signals?limit=20&offset=0")
    
    @task(1)
    def get_positions(self):
        self.client.get("/v1/positions?limit=20&offset=0")
    
    @task(1)
    def estimate_position(self):
        self.client.post("/v1/positions/estimate", json={"signal_id": 1})
```

**Run Tests**:
```bash
locust -f tests/performance/locustfile.py --host=http://localhost:8003
```

**Performance Baseline**:
- P95 response time: <2 seconds
- Error rate: <1%
- Throughput: >100 RPS

### Stress Testing

**Goal**: Find breaking point of the system

**Procedure**:
1. Gradually increase load
2. Monitor system metrics
3. Identify bottlenecks
4. Document breaking point

## Contract Tests

### API Contract Tests

**Framework**: Pact

**Location**: `tests/contract/`

**Purpose**: Ensure API contracts between services are maintained

**Example**:
```python
# tests/contract/test_decision_engine_portfolio_contract.py
from pact import Consumer, Provider

pact = Consumer('PortfolioService').has_pact_with(Provider('DecisionEngineService'))

def test_get_signal_contract():
    expected = {
        'id': 1,
        'market': 'BTCUSDT',
        'signal_type': 'PULLBACK_BUY',
        'entry_price': 35000.0,
    }
    
    (pact
     .given('signal 1 exists')
     .upon_receiving('a request for signal 1')
     .with_request('get', '/v1/signals/1')
     .will_respond_with(200, body=expected))
    
    with pact:
        result = portfolio_service.get_signal(1)
        assert result['id'] == 1
```

**Run Tests**:
```bash
pytest tests/contract/ -v
```

## Test Data Management

### Test Fixtures

**Location**: `tests/fixtures/`

**Example**:
```python
# tests/fixtures/signal_fixtures.py
import pytest

@pytest.fixture
def sample_signal():
    return {
        'market': 'BTCUSDT',
        'signal_type': 'PULLBACK_BUY',
        'entry_price': 35000.0,
        'stop_loss_price': 34000.0,
        'profit_target_price': 37000.0,
    }
```

### Mock Data

**Location**: `tests/mocks/`

**Purpose**: Mock external API responses

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run unit tests
        run: pytest services/ -v --cov --cov-report=xml
      
      - name: Run integration tests
        run: pytest tests/integration/ -v -m integration
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Test Reporting

### Coverage Reports

**Tool**: pytest-cov

**Command**:
```bash
pytest --cov=services --cov-report=html
```

**Output**: `htmlcov/index.html`

### Test Results

**Tool**: pytest-html

**Command**:
```bash
pytest --html=report.html
```

## Best Practices

1. **Write tests first** (TDD when possible)
2. **Keep tests independent** (no test should depend on another)
3. **Use descriptive test names** (test_calculate_position_size_with_zero_balance)
4. **Test edge cases** (zero, negative, null, empty)
5. **Mock external dependencies** (APIs, databases)
6. **Clean up test data** (use fixtures and teardown)
7. **Run tests frequently** (before commit, in CI/CD)
8. **Maintain test coverage** (>70% for all services)

---

**Last Updated**: 2025-11-09

