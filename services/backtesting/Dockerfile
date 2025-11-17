FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/backtesting/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/backtesting ./services/backtesting
COPY services/portfolio ./services/portfolio
COPY services/decision_engine ./services/decision_engine
COPY shared ./shared
COPY database_migrations ./database_migrations

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8004

# Run the application
CMD ["python", "-m", "uvicorn", "services.backtesting.app.main:app", "--host", "0.0.0.0", "--port", "8004"]

