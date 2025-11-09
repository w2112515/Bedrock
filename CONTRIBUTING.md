# Contributing to Project Bedrock

Thank you for your interest in contributing to Project Bedrock! This document provides guidelines for contributing to the project.

## Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

**Positive behavior includes**:
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community

**Unacceptable behavior includes**:
- Trolling, insulting/derogatory comments, and personal attacks
- Public or private harassment
- Publishing others' private information without permission
- Other conduct which could reasonably be considered inappropriate

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates.

**Bug Report Template**:
```markdown
**Description**: Brief description of the bug

**Steps to Reproduce**:
1. Step 1
2. Step 2
3. Step 3

**Expected Behavior**: What should happen

**Actual Behavior**: What actually happens

**Environment**:
- OS: [e.g., Windows 11, Ubuntu 22.04]
- Python Version: [e.g., 3.11.5]
- Docker Version: [e.g., 24.0.5]

**Additional Context**: Any other relevant information
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues.

**Enhancement Request Template**:
```markdown
**Feature Description**: Brief description of the feature

**Use Case**: Why is this feature needed?

**Proposed Solution**: How should this feature work?

**Alternatives Considered**: Other approaches you've considered

**Additional Context**: Any other relevant information
```

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes**
4. **Write tests** for your changes
5. **Run tests**: `pytest`
6. **Run linters**: `black .`, `flake8`, `mypy`
7. **Commit your changes**: `git commit -m "Add feature: your feature description"`
8. **Push to your fork**: `git push origin feature/your-feature-name`
9. **Create a Pull Request**

## Development Setup

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+
- Node.js 18+
- Git 2.x+

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd projectBedrock
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r shared/requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Install Node.js dependencies**
   ```bash
   cd webapp
   npm install
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Start infrastructure**
   ```bash
   docker-compose up -d postgres redis
   ```

6. **Run migrations**
   ```bash
   cd database_migrations
   alembic upgrade head
   ```

## Coding Standards

### Python Code Style

- Follow [PEP 8](https://pep8.org/)
- Use [Black](https://black.readthedocs.io/) for formatting
- Use [flake8](https://flake8.pycqa.org/) for linting
- Use [mypy](http://mypy-lang.org/) for type checking
- Maximum line length: 100 characters

**Example**:
```python
from typing import Optional

def calculate_position_size(
    account_balance: float,
    risk_percentage: float,
    stop_loss_distance: float
) -> float:
    """
    Calculate position size based on risk management rules.
    
    Args:
        account_balance: Total account balance
        risk_percentage: Risk percentage (e.g., 0.02 for 2%)
        stop_loss_distance: Distance to stop loss in percentage
    
    Returns:
        Position size in base currency
    """
    risk_amount = account_balance * risk_percentage
    position_size = risk_amount / stop_loss_distance
    return position_size
```

### TypeScript Code Style

- Follow [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- Use [Prettier](https://prettier.io/) for formatting
- Use [ESLint](https://eslint.org/) for linting
- Use TypeScript strict mode

**Example**:
```typescript
interface PositionEstimation {
  estimatedPositionSize: number;
  estimatedCost: number;
  riskPercentage: number;
  positionWeightUsed: number;
}

export const estimatePosition = async (
  signalId: number
): Promise<PositionEstimation> => {
  const response = await api.post('/v1/positions/estimate', { signal_id: signalId });
  return response.data;
};
```

### Commit Message Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/):

**Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(portfolio): add position sizing calculation

Implement position sizing based on suggested weight from signals.
Uses Plan A approach where strategy layer suggests weight.

Closes #123
```

```
fix(datahub): handle Binance API rate limit

Add exponential backoff retry logic for rate limit errors.

Fixes #456
```

## Testing Guidelines

### Unit Tests

- Write unit tests for all new code
- Aim for >70% code coverage
- Use pytest for Python tests
- Use Jest for TypeScript tests

**Python Example**:
```python
def test_calculate_position_size():
    account_balance = 10000.0
    risk_percentage = 0.02
    stop_loss_distance = 0.05
    
    result = calculate_position_size(account_balance, risk_percentage, stop_loss_distance)
    
    assert result == 4000.0
```

**TypeScript Example**:
```typescript
describe('estimatePosition', () => {
  it('should return position estimation', async () => {
    const signalId = 1;
    const result = await estimatePosition(signalId);
    
    expect(result.estimatedPositionSize).toBeGreaterThan(0);
    expect(result.riskPercentage).toBeLessThanOrEqual(2.0);
  });
});
```

### Integration Tests

- Test service interactions
- Use test database
- Clean up test data after tests

### E2E Tests

- Test complete user flows
- Use Playwright for frontend E2E tests

## Documentation Guidelines

- Update documentation when changing code
- Follow [Documentation Maintenance Checklist](docs/DOCUMENTATION_MAINTENANCE.md)
- Use clear, concise language
- Provide code examples

## Review Process

### Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Code follows style guidelines
- [ ] Tests are written and passing
- [ ] Documentation is updated
- [ ] Commit messages follow conventions
- [ ] No merge conflicts
- [ ] CI/CD pipeline passes

### Code Review Guidelines

**For Reviewers**:
- Be respectful and constructive
- Focus on code quality, not personal preferences
- Suggest improvements, don't demand changes
- Approve when code meets standards

**For Authors**:
- Respond to all comments
- Make requested changes or explain why not
- Be open to feedback
- Thank reviewers for their time

## Release Process

1. **Create release branch**: `git checkout -b release/v1.0.0`
2. **Update version numbers**
3. **Update CHANGELOG.md**
4. **Run full test suite**
5. **Create pull request to main**
6. **Merge after approval**
7. **Tag release**: `git tag v1.0.0`
8. **Push tag**: `git push origin v1.0.0`
9. **Deploy to production**

## Questions?

If you have questions, please:
1. Check existing documentation
2. Search existing issues
3. Ask in project discussions
4. Contact the maintainers

Thank you for contributing to Project Bedrock! 🚀

---

**Last Updated**: 2025-11-09

