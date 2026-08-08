import time
import datetime
from backend.services.job_types import JobType
from backend.services.job_result import JobResult, JobStatus
from backend.services.scrape_service import scrape_product
from backend.tracing import get_traced_logger, start_span, end_span, set_context
from backend.celery_app import celery_app
from backend.config import settings

logger = get_traced_logger("worker")

@celery_app.task(bind=True, max_retries=settings.MAX_RETRIES, acks_late=True)
def execute_job(
    self,
    job_id: str, 
    job_type: str, 
    request_id: str, 
    user_id: int, 
    product_id: int, 
    created_at_ts: float,
    trace_id: str = None,
    parent_span_id: str = None
):
    """
    Executes a job asynchronously via Celery. Gracefully handles exceptions and logs structured metadata.
    """
    worker_span_id = start_span("Worker")
    
    start_time = time.time()
    queue_time_ms = int((start_time - created_at_ts) * 1000)
    
    # Observe queue wait time
    try:
        from backend.metrics import CELERY_QUEUE_WAIT_TIME
        CELERY_QUEUE_WAIT_TIME.observe(queue_time_ms / 1000.0)
    except Exception:
        pass
    
    perf_start = time.perf_counter()
    attempt = self.request.retries + 1

    set_context(
        trace_id=trace_id,
        span_id=worker_span_id,
        parent_span_id=parent_span_id,
        span_name="Worker",
        request_id=request_id,
        job_id=job_id,
        job_type=job_type,
        user_id=user_id,
        product_id=product_id,
        attempt=attempt,
        max_attempts=settings.MAX_RETRIES,
        queue_time_ms=queue_time_ms
    )

    result = JobResult(
        job_id=job_id,
        status=JobStatus.RUNNING,
        started_at=datetime.datetime.now(datetime.timezone.utc),
        request_id=request_id,
        user_id=user_id,
        product_id=product_id
    )
    
    logger.info(f"Job {job_id} started.", extra={"event": "job_started", "status": "RUNNING", "queue_name": settings.QUEUE_NAME, "task_id": self.request.id})
    
    try:
        if job_type == JobType.SCRAPE_PRODUCT:
            scrape_product(product_id)
            # Check DB product status to reflect actual scraper outcome in Celery result
            try:
                from backend.database import SessionLocal
                from backend.models import Product
                db = SessionLocal()
                db_prod = db.query(Product).filter(Product.id == product_id).first()
                if db_prod and db_prod.status == "FAILED":
                    result.status = JobStatus.FAILED
                    result.error = db_prod.last_failure_reason or "Scraper failed to extract product data"
                else:
                    result.status = JobStatus.SUCCESS
                db.close()
            except Exception:
                result.status = JobStatus.SUCCESS
        else:
            logger.warning(f"Unknown job type: {job_type}")
            result.status = JobStatus.SUCCESS

        try:
            from backend.metrics import CELERY_JOBS_COMPLETED
            CELERY_JOBS_COMPLETED.labels(job_type=job_type, status=result.status.value if hasattr(result.status, "value") else str(result.status)).inc()
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Job {job_id} failed on attempt {attempt}: {e}", exc_info=True, extra={"event": "job_failed", "status": "FAILED", "queue_name": settings.QUEUE_NAME, "task_id": self.request.id})
        result.status = JobStatus.FAILED
        result.error = str(e)
        
        try:
            from backend.metrics import EXCEPTION_COUNTER, CELERY_JOBS_COMPLETED
            from sqlalchemy.exc import SQLAlchemyError
            from redis.exceptions import RedisError
            
            if isinstance(e, SQLAlchemyError):
                EXCEPTION_COUNTER.labels(exception_type="DatabaseError").inc()
            elif isinstance(e, RedisError):
                EXCEPTION_COUNTER.labels(exception_type="RedisError").inc()
            elif isinstance(e, (TimeoutError, asyncio.TimeoutError)) or "timeout" in str(e).lower():
                EXCEPTION_COUNTER.labels(exception_type="TimeoutError").inc()
            elif "playwright" in type(e).__name__.lower() or "playwright" in str(e).lower():
                EXCEPTION_COUNTER.labels(exception_type="PlaywrightError").inc()
            elif "twilio" in type(e).__name__.lower():
                EXCEPTION_COUNTER.labels(exception_type="TwilioError").inc()
            else:
                EXCEPTION_COUNTER.labels(exception_type="UnknownError").inc()
                
            CELERY_JOBS_COMPLETED.labels(job_type=job_type, status="FAILED").inc()
        except Exception:
            pass
            
        perf_end = time.perf_counter()
        execution_time_ms = int((perf_end - perf_start) * 1000)
        set_context(execution_time_ms=execution_time_ms)
        end_span(previous_span_id=parent_span_id)
        
        if attempt <= settings.MAX_RETRIES:
            countdown = 2 ** attempt  # Exponential backoff
            raise self.retry(exc=e, countdown=countdown)
        else:
            logger.error(f"DEAD LETTER: Job {job_id} permanently failed after {settings.MAX_RETRIES} retries.", extra={"event": "job_dead_letter", "status": "DEAD_LETTER", "error_reason": str(e), "queue_name": settings.QUEUE_NAME, "task_id": self.request.id})
            
            # Real Dead Letter Queue in Redis
            try:
                import json
                import redis
                r = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_timeout=2.0)
                dead_job = {
                    "job_id": job_id,
                    "task_id": self.request.id,
                    "job_type": job_type,
                    "product_id": product_id,
                    "user_id": user_id,
                    "error": str(e),
                    "failed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
                r.rpush("celery_dead_letter_queue", json.dumps(dead_job))
            except Exception as dl_err:
                logger.error(f"Failed to push to Dead Letter Queue: {dl_err}")
                
            # The database state is handled by scrape_service which marks status="FAILED" and retry_count on the Product
            return result.dict()
            
    perf_end = time.perf_counter()
    execution_time_ms = int((perf_end - perf_start) * 1000)
    
    result.finished_at = datetime.datetime.now(datetime.timezone.utc)
    result.execution_time = execution_time_ms / 1000.0
    
    set_context(execution_time_ms=execution_time_ms)
    
    # Observe execution duration
    try:
        from backend.metrics import CELERY_WORKER_EXECUTION_TIME
        CELERY_WORKER_EXECUTION_TIME.labels(job_type=job_type).observe(execution_time_ms / 1000.0)
    except Exception:
        pass
        
    status_str = result.status.value
    logger.info(
        f"Job {job_id} finished with status {status_str}.", 
        extra={
            "event": "job_finished",
            "status": status_str,
            "queue_name": settings.QUEUE_NAME,
            "task_id": self.request.id
        }
    )
    
    end_span(previous_span_id=parent_span_id)
    
    return result.dict()
