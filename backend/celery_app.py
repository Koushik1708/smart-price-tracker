from celery import Celery
from backend.config import settings
import os

celery_app = Celery(
    "letsgo_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["backend.services.worker"]
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    broker_connection_retry_on_startup=False,
    broker_connection_timeout=2.0,
    broker_connection_retry=True,
    broker_connection_max_retries=2,
    broker_transport_options={'visibility_timeout': int(os.getenv("CELERY_VISIBILITY_TIMEOUT", "3600"))},
    
    task_time_limit=settings.PLAYWRIGHT_TIMEOUT // 1000 + 30,  # e.g., 90s
    task_soft_time_limit=settings.PLAYWRIGHT_TIMEOUT // 1000 + 15, # e.g., 75s
    
    worker_concurrency=settings.CELERY_CONCURRENCY,
    
    task_default_queue=settings.QUEUE_NAME,
    
    # Optional graceful shutdown configurations
    worker_cancel_long_running_tasks_on_connection_loss=True,
    
    # Task routing if needed later
    task_routes={
        "backend.services.worker.execute_job": {"queue": settings.QUEUE_NAME}
    }
)

if settings.CELERY_BROKER_URL.startswith("rediss://"):
    import ssl
    celery_app.conf.update(
        broker_use_ssl={'ssl_cert_reqs': ssl.CERT_REQUIRED},
        redis_backend_use_ssl={'ssl_cert_reqs': ssl.CERT_REQUIRED},
    )


from celery.signals import worker_process_init
from backend.database import engine
from backend.tracing import get_traced_logger

logger = get_traced_logger(__name__)

@worker_process_init.connect
def init_worker(**kwargs):
    """
    Called when a Celery worker child process is initialized.
    Disposes of the inherited database connection pool to ensure clean connections per worker.
    """
    logger.info("Celery worker process initialized. Disposing SQLAlchemy engine pool to prevent stale inherited connections.")
    engine.dispose()

from celery.signals import worker_ready

@worker_ready.connect
def cleanup_stuck_tasks(sender, **kwargs):
    """
    On worker startup, reset any products stuck in SCRAPING status back to PENDING
    so that redelivered tasks can execute them successfully.
    """
    logger.info("Worker ready. Cleaning up stuck SCRAPING products...")
    from backend.database import SessionLocal
    from backend.models import Product
    db = SessionLocal()
    try:
        stuck_products = db.query(Product).filter(Product.status == "SCRAPING").all()
        if stuck_products:
            logger.info(f"Found {len(stuck_products)} stuck SCRAPING products. Resetting to PENDING.")
            for p in stuck_products:
                p.status = "PENDING"
            db.commit()
    except Exception as e:
        logger.error(f"Failed to cleanup stuck tasks on worker startup: {e}")
        db.rollback()
    finally:
        db.close()
