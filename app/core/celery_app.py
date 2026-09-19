from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "document_intelligence_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 minute timeout
    task_soft_time_limit=1500,  # 25 minute soft timeout
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=True,
)

# Auto-discover tasks in worker module
celery_app.autodiscover_tasks(["app.workers"])
