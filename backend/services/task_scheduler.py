import uuid
import time
from backend.services.job_types import JobType
from backend.services.worker import execute_job
from backend.tracing import start_span, end_span, ctx_trace_id, ctx_span_id, get_traced_logger

logger = get_traced_logger(__name__)

def schedule_scrape(
    product_id: int, 
    user_id: int, 
    request_id: str
) -> str:
    """
    Schedules a SCRAPE_PRODUCT job via Celery.
    """
    job_id = str(uuid.uuid4())
    created_at_ts = time.time()
    
    prev_span = ctx_span_id.get()
    scheduler_span = start_span("Scheduler")
    trace_id = ctx_trace_id.get()
    
    logger.info(f"Enqueuing job {job_id}", extra={
        "event": "job_enqueued", 
        "job_id": job_id, 
        "job_type": JobType.SCRAPE_PRODUCT.value,
        "product_id": product_id,
        "user_id": user_id
    })
    
    try:
        import redis
        from backend.config import settings
        broker_url = settings.CELERY_BROKER_URL.strip()
        kwargs = {"socket_connect_timeout": 5.0, "socket_timeout": 5.0}
        if broker_url.startswith("rediss://") and "ssl_cert_reqs" not in broker_url:
            kwargs["ssl_cert_reqs"] = "none"
        r = redis.Redis.from_url(broker_url, **kwargs)
        r.ping()
    except Exception as e:
        logger.error(f"Redis ping failed: {e}", exc_info=True, extra={
            "event": "broker_offline",
            "job_id": job_id,
            "trace_id": trace_id
        })
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Service Unavailable: Message broker offline")

    try:
        execute_job.apply_async(
            kwargs={
                "job_id": job_id,
                "job_type": JobType.SCRAPE_PRODUCT.value,
                "request_id": request_id,
                "user_id": user_id,
                "product_id": product_id,
                "created_at_ts": created_at_ts,
                "trace_id": trace_id,
                "parent_span_id": scheduler_span
            },
            task_id=job_id,
            retry=True,
            retry_policy={
                'max_retries': 2,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.5,
            }
        )
    except Exception as e:
        logger.error(f"Failed to enqueue job {job_id}: {e}", exc_info=True, extra={
            "event": "enqueue_failed",
            "error_type": type(e).__name__,
            "job_id": job_id,
            "trace_id": trace_id
        })
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Service Unavailable: Message broker offline")
    
    end_span(previous_span_id=prev_span)
    
    return job_id
