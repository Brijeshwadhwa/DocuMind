from celery import shared_task
from app.core.celery_app import celery_app
from app.core.logging import logger
from app.processors.pipeline import DocumentPipeline


@celery_app.task(name="tasks.process_document", bind=True, max_retries=2)
def process_document_task(self, document_id: str):
    """
    Celery background worker task that invokes the DocumentPipeline.
    """
    logger.info(f"[Celery Worker] Received task for document {document_id}")
    try:
        pipeline = DocumentPipeline()
        success = pipeline.process_document(document_id)
        logger.info(f"[Celery Worker] Finished task for document {document_id}: success={success}")
        return {"document_id": document_id, "success": success}
    except Exception as exc:
        logger.error(f"[Celery Worker] Task failed for document {document_id}: {exc}")
        # Retry with exponential backoff on unexpected transient failures
        raise self.retry(exc=exc, countdown=5 * (2 ** self.request.retries))


def dispatch_document_processing(document_id: str, db=None):
    """
    Dispatches document processing.
    If CELERY_TASK_ALWAYS_EAGER=True, execution runs in-process with the current database session.
    Otherwise, enqueues to Celery broker.
    """
    from app.core.config import settings
    if settings.CELERY_TASK_ALWAYS_EAGER:
        logger.info(f"CELERY_TASK_ALWAYS_EAGER is True. Processing document {document_id} synchronously.")
        pipeline = DocumentPipeline(db=db)
        pipeline.process_document(document_id)
        return

    try:
        logger.info(f"Enqueueing background processing task for document {document_id}")
        process_document_task.delay(document_id)
    except Exception as e:
        logger.warning(
            f"Celery queue dispatch failed ({e}). Running processing synchronously as fallback."
        )
        pipeline = DocumentPipeline(db=db)
        pipeline.process_document(document_id)
