from celery import Celery
from app.core.config import settings

# We initialize the Celery app.
# The 'broker' is where the tasks are sent (Redis).
# The 'backend' is where the results of the tasks are stored (Redis).
celery_app = Celery(
    "forgemind_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    include=['app.worker'],
)

# This tells Celery where to find the task functions.
# We will put our actual logic in backend/app/worker.py
