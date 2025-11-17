"""
Celery application configuration.

Configures Celery for asynchronous backtest execution.
"""

import sys
import os
from celery import Celery

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from services.backtesting.app.core.config import settings

# Create Celery app
celery_app = Celery(
    "backtesting",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(['services.backtesting.app.tasks'])

