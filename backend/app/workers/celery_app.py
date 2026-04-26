from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "rx_explainer",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    result_expires=3600,        # results kept for 1 hour
)
