"""
app/tasks/import_tasks.py
==========================
Celery task stubs for async import processing.

To enable Celery:
    1. pip install celery redis
    2. Add CELERY_ENABLED=true and CELERY_BROKER_URL=redis://localhost:6379/0 to .env
    3. Start worker: celery -A app.tasks.celery_app worker --loglevel=info

Until then, tasks run synchronously (inline) as a fallback.
"""
import os


def _is_celery_enabled() -> bool:
    return os.environ.get("CELERY_ENABLED", "false").lower() == "true"


def _get_celery_app():
    """Lazy-load Celery app only if enabled."""
    if not _is_celery_enabled():
        return None
    try:
        from celery import Celery
        broker = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
        return Celery("financeos", broker=broker)
    except ImportError:
        return None


def process_statement_async(import_history_id: int, user_id: int) -> None:
    """
    TODO: Process a large statement file asynchronously.
    Currently runs synchronously. Wrap with @celery.task when Celery is enabled.
    """
    # Placeholder — actual parsing already done synchronously in statement_import_service
    # When Celery is integrated, move the parsing loop here and update history row status
    pass


def run_ocr_async(upload_id: str, user_id: int) -> None:
    """
    TODO: Run OCR on an uploaded receipt image asynchronously.
    Implement when pytesseract / Google Vision integration is added.
    """
    raise NotImplementedError("OCR async task not yet implemented.")


def run_ai_analysis_async(user_id: int) -> None:
    """
    TODO: Run full AI spending analysis asynchronously.
    Currently ai_insights_service runs synchronously on each request.
    Move heavy analysis here when Celery is enabled.
    """
    pass
