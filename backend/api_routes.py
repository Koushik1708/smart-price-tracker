from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.database import get_db
from backend.notifications import TwilioSandboxProvider, get_notifier, SUPPORTED_CHANNELS, build_alert_confirmation_message
from backend.auth import get_current_user
from backend.models import User, Product, PriceSnapshot, AlertThreshold
from backend.services.task_scheduler import schedule_scrape
from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import List, Literal
import os
from backend.config import settings

router = APIRouter()

ALLOWED_AMAZON_DOMAINS = ("amazon.in", "amzn.in", "amzn.to")
ALLOWED_FLIPKART_DOMAINS = ("flipkart.com", "dl.flipkart.com", "fkrt.it")

def is_valid_domain(url: str) -> bool:
    url_str = str(url).strip()
    if not url_str.startswith(("http://", "https://")):
        url_str = "https://" + url_str
    try:
        parsed = urlparse(url_str)
        host = (parsed.hostname or "").lower()
        if not host:
            return False
        is_amazon = any(host == d or host.endswith("." + d) for d in ALLOWED_AMAZON_DOMAINS)
        is_flipkart = any(host == d or host.endswith("." + d) for d in ALLOWED_FLIPKART_DOMAINS)
        return is_amazon or is_flipkart
    except Exception:
        return False

class ProductCreate(BaseModel):
    url: HttpUrl = Field(..., description="The Amazon India or Flipkart product URL")

    @field_validator("url")
    def validate_url_domain(cls, v):
        if not is_valid_domain(str(v)):
            raise ValueError("Only official Amazon India (amazon.in, amzn.in) and Flipkart (flipkart.com) URLs are supported.")
        return v

from typing import Optional

class ProductResponse(BaseModel):
    id: int
    url: str
    title: str
    platform: str
    product_id: str
    status: str = "PENDING"
    image_url: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    
    class Config:
        from_attributes = True

import requests
import re
from urllib.parse import urlparse, parse_qs

def canonicalize_url(url: str) -> dict:
    url_str = str(url).strip()
    if not url_str.startswith(("http://", "https://")):
        url_str = "https://" + url_str
        
    if not is_valid_domain(url_str):
        raise ValueError("Only official Amazon India and Flipkart URLs are supported.")
        
    parsed_input = urlparse(url_str)
    host_input = (parsed_input.hostname or "").lower()
    
    is_amazon = any(host_input == d or host_input.endswith("." + d) for d in ALLOWED_AMAZON_DOMAINS)
    is_flipkart = any(host_input == d or host_input.endswith("." + d) for d in ALLOWED_FLIPKART_DOMAINS)
    
    if is_amazon:
        platform = "amazon"
        match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", url_str, re.IGNORECASE)
        if match:
            pid = match.group(1).upper()
            canonical_url = f"https://www.amazon.in/dp/{pid}"
        else:
            pid = "unknown"
            canonical_url = url_str
    elif is_flipkart:
        platform = "flipkart"
        match = re.search(r"/p/(itm[a-zA-Z0-9]+)", url_str)
        if match:
            itm_id = match.group(1)
            qs = parse_qs(parsed_input.query)
            pid = qs.get("pid", [itm_id])[0]
            canonical_url = f"https://www.flipkart.com{parsed_input.path}?pid={pid}"
        else:
            pid = "unknown"
            canonical_url = url_str
    else:
        raise ValueError("Unsupported platform")
        
    return {
        "platform": platform,
        "pid": pid,
        "canonical_url": canonical_url
    }

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/live")
def get_live():
    return {"status": "alive"}

@router.get("/ready")
def get_ready(db: Session = Depends(get_db)):
    from backend.config import settings
    # DB
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Database not ready")
        
    # Redis
    try:
        import redis
        broker_url = settings.CELERY_BROKER_URL.strip()
        kwargs = {"socket_connect_timeout": 5.0, "socket_timeout": 5.0}
        if broker_url.startswith("rediss://") and "ssl_cert_reqs" not in broker_url:
            kwargs["ssl_cert_reqs"] = "none"
        r = redis.Redis.from_url(broker_url, **kwargs)
        r.ping()
    except Exception:
        raise HTTPException(status_code=503, detail="Redis broker not ready")
        
@router.get("/health")
def get_health(request: Request, response: Response, db: Session = Depends(get_db)):
    from backend.config import settings
    import time
    import datetime
    from fastapi import status as http_status

    health_status = {
        "status": "healthy",
        "summary": "All systems operational.",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": int(time.time() - settings.START_TIME),
        "database": "unknown",
        "redis": "unknown",
        "celery": "unknown",
        "notifications": "unknown",
        "disk": "unknown",
        "memory": "unknown",
        "cpu": "unknown",
        "queue": "unknown",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "request_id": getattr(request.state, "request_id", "unknown"),
        "env_keys": sorted(list(os.environ.keys()))
    }

    critical_failures = []

    # 1. Check Database (critical)
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "healthy"
    except Exception:
        health_status["database"] = "unhealthy"
        critical_failures.append("database")

    # 2. Check Redis (critical)
    try:
        import redis
        broker_url = settings.CELERY_BROKER_URL.strip()
        kwargs = {"socket_connect_timeout": 5.0, "socket_timeout": 5.0}
        if broker_url.startswith("rediss://") and "ssl_cert_reqs" not in broker_url:
            kwargs["ssl_cert_reqs"] = "none"
        r = redis.Redis.from_url(broker_url, **kwargs)
        r.ping()
        health_status["redis"] = "healthy"
    except Exception as e:
        health_status["redis"] = "unhealthy"
        health_status["redis_error"] = f"{type(e).__name__}: {str(e)}"
        critical_failures.append("redis")

    # 3. Check Celery Worker (critical)
    try:
        import redis
        broker_url = settings.CELERY_BROKER_URL.strip()
        kwargs = {"socket_connect_timeout": 5.0, "socket_timeout": 5.0}
        if broker_url.startswith("rediss://") and "ssl_cert_reqs" not in broker_url:
            kwargs["ssl_cert_reqs"] = "none"
        r_celery = redis.Redis.from_url(broker_url, **kwargs)
        r_celery.ping()
        health_status["celery"] = "healthy"
    except Exception as e:
        health_status["celery"] = "unhealthy"
        health_status["celery_error"] = f"{type(e).__name__}: {str(e)}"
        critical_failures.append("celery")

    degraded_reasons = []

    # 4. Check Memory (warning if >= 90%)
    try:
        import psutil
        mem = psutil.virtual_memory()
        is_mem_warning = mem.percent >= 90.0
        health_status["memory"] = {
            "status": "warning" if is_mem_warning else "healthy",
            "percent": round(mem.percent, 1),
            "available_mb": round(mem.available / (2**20), 2)
        }
        if is_mem_warning:
            degraded_reasons.append("High host memory usage detected")
    except Exception:
        health_status["memory"] = {"status": "warning", "percent": 0.0, "available_mb": 0.0}
        degraded_reasons.append("Memory check failed")

    # 5. Check Disk Space (warning if 10-15%, unhealthy if <= 10%)
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        free_percent = (free / total) * 100
        if free_percent <= 10.0:
            disk_st = "unhealthy"
            degraded_reasons.append("Critical low disk space")
        elif free_percent <= 15.0:
            disk_st = "warning"
            degraded_reasons.append("Low disk space warning")
        else:
            disk_st = "healthy"

        health_status["disk"] = {
            "status": disk_st,
            "free_percent": round(free_percent, 2),
            "free_gb": round(free / (2**30), 2)
        }
    except Exception:
        health_status["disk"] = {"status": "warning", "free_percent": 0.0, "free_gb": 0.0}

    # 6. Check CPU
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=None)
        is_cpu_warning = cpu_percent >= 90.0
        health_status["cpu"] = {
            "status": "warning" if is_cpu_warning else "healthy",
            "percent": round(cpu_percent, 1)
        }
        if is_cpu_warning:
            degraded_reasons.append("High CPU usage detected")
    except Exception:
        health_status["cpu"] = {"status": "healthy", "percent": 0.0}

    # 7. Check Queue Depth (warning if >= 50)
    try:
        import redis
        r = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_timeout=2.0)
        queue_len = r.llen(settings.QUEUE_NAME)
        is_queue_warning = queue_len >= 50
        health_status["queue"] = {
            "status": "warning" if is_queue_warning else "healthy",
            "depth": queue_len
        }
        if is_queue_warning:
            degraded_reasons.append("High queue depth detected")

        try:
            from backend.metrics import CELERY_QUEUE_DEPTH
            CELERY_QUEUE_DEPTH.labels(queue=settings.QUEUE_NAME).set(queue_len)
        except Exception:
            pass
    except Exception:
        health_status["queue"] = {"status": "healthy", "depth": 0}

    # 8. Check Notifications
    whatsapp_ok = bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_WHATSAPP_NUMBER)
    telegram_ok = bool(settings.TELEGRAM_BOT_TOKEN)
    health_status["notifications"] = {
        "whatsapp": "configured" if whatsapp_ok else "not_configured",
        "telegram": "configured" if telegram_ok else "not_configured"
    }
    if whatsapp_ok or telegram_ok:
        health_status["notifications"]["status"] = "healthy"
    else:
        health_status["notifications"]["status"] = "not_configured"

    # Decision Logic & HTTP Status Code Mapping:
    if critical_failures:
        health_status["status"] = "unhealthy"
        health_status["summary"] = f"Critical dependencies unavailable: {', '.join(critical_failures)}."
        response.status_code = http_status.HTTP_503_SERVICE_UNAVAILABLE
    elif degraded_reasons:
        health_status["status"] = "degraded"
        health_status["summary"] = f"Core services operational. {'. '.join(degraded_reasons)}."
        response.status_code = http_status.HTTP_200_OK
    else:
        health_status["status"] = "healthy"
        health_status["summary"] = "All systems operational."
        response.status_code = http_status.HTTP_200_OK

    return health_status



@router.get("/version")
def get_version():
    import datetime
    return {
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "build_date": datetime.date.today().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "git_commit": os.getenv("VERCEL_GIT_COMMIT_SHA", "unknown")
    }

@router.get("/metrics")
def get_metrics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total_products = db.query(Product).filter(Product.user_id == current_user.id).count()
    successful_scrapes = db.query(Product).filter(Product.user_id == current_user.id, Product.status == "SUCCESS").count()
    failed_scrapes = db.query(Product).filter(Product.user_id == current_user.id, Product.status == "FAILED").count()
    pending_products = db.query(Product).filter(Product.user_id == current_user.id, Product.status == "PENDING").count()
    active_alerts = db.query(AlertThreshold).filter(AlertThreshold.user_id == current_user.id, AlertThreshold.status == "ACTIVE").count()
    
    # Fake discounts are tied to products
    product_ids = [p.id for p in db.query(Product.id).filter(Product.user_id == current_user.id).all()]
    fake_discounts_detected = db.query(PriceSnapshot).filter(PriceSnapshot.product_id.in_(product_ids), PriceSnapshot.is_fake_discount == True).count() if product_ids else 0
    
    return {
        "total_products": total_products,
        "successful_scrapes": successful_scrapes,
        "failed_scrapes": failed_scrapes,
        "pending_products": pending_products,
        "active_alerts": active_alerts,
        "fake_discounts_detected": fake_discounts_detected
    }

@router.post("/products/track", response_model=ProductResponse)
@limiter.limit(settings.TRACK_RATE_LIMIT)
def track_product(request: Request, product: ProductCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.config import settings
    from backend.services.audit_service import log_audit_event
    
    # Enforce operational product tracking limit per user
    user_prod_count = db.query(Product).filter(Product.user_id == current_user.id).count()
    if user_prod_count >= settings.MAX_PRODUCTS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"Product limit reached. Maximum allowed tracked products per user is {settings.MAX_PRODUCTS_PER_USER}."
        )

    try:
        canonical_data = canonicalize_url(str(product.url))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    db_product = db.query(Product).filter(Product.url == canonical_data["canonical_url"], Product.user_id == current_user.id).first()
    if db_product:
        from fastapi.responses import JSONResponse
        import datetime
        req_id = getattr(request.state, "request_id", "unknown")
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return JSONResponse(status_code=409, content={
            "success": False, 
            "message": "Product already tracked", 
            "error_code": "PRODUCT_ALREADY_TRACKED",
            "error": {
                "code": "PRODUCT_ALREADY_TRACKED",
                "message": "Product already tracked",
                "details": None
            },
            "request_id": req_id,
            "timestamp": timestamp
        })
        
    new_product = Product(
        user_id=current_user.id,
        url=canonical_data["canonical_url"],
        platform=canonical_data["platform"],
        product_id=canonical_data["pid"],
        title="Tracking Pending...",
        status="PENDING",
        retry_count=0
    )
    db.add(new_product)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        from sqlalchemy.exc import IntegrityError
        if isinstance(e, IntegrityError):
            from fastapi.responses import JSONResponse
            import datetime
            req_id = getattr(request.state, "request_id", "unknown")
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            return JSONResponse(status_code=409, content={
                "success": False, 
                "message": "Product already tracked", 
                "error_code": "PRODUCT_ALREADY_TRACKED",
                "error": {
                    "code": "PRODUCT_ALREADY_TRACKED",
                    "message": "Product already tracked",
                    "details": None
                },
                "request_id": req_id,
                "timestamp": timestamp
            })
        raise
        
    db.refresh(new_product)
    req_id = getattr(request.state, "request_id", "unknown")
    schedule_scrape(new_product.id, current_user.id, req_id)
    
    log_audit_event(
        db,
        action="PRODUCT_TRACKED",
        outcome="SUCCESS",
        user_id=current_user.id,
        details={"product_id": new_product.id, "platform": new_product.platform, "url": new_product.url},
        request=request
    )
    
    return new_product

@router.delete("/products/{product_id}")
def delete_product(request: Request, product_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.services.audit_service import log_audit_event
    product = db.query(Product).filter(Product.id == product_id, Product.user_id == current_user.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    db.delete(product)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        from backend.tracing import get_traced_logger
        logger = get_traced_logger(__name__)
        logger.error(f"Failed to delete product {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database transaction failed")
        
    log_audit_event(
        db,
        action="PRODUCT_DELETED",
        outcome="SUCCESS",
        user_id=current_user.id,
        details={"product_id": product_id},
        request=request
    )
    return {"message": "Product deleted successfully"}

@router.post("/products/{product_id}/retry")
@limiter.limit("5/minute")
def retry_failed_product(request: Request, product_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id, Product.user_id == current_user.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    if product.status != "FAILED":
        raise HTTPException(status_code=400, detail="Only failed products can be retried")
        
    product.status = "PENDING"
    product.retry_count = 0  # Reset retry count on manual retry
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        from backend.tracing import get_traced_logger
        logger = get_traced_logger(__name__)
        logger.error(f"Failed to retry product {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database transaction failed")
        
    from backend.services.task_scheduler import schedule_scrape
    req_id = getattr(request.state, "request_id", "unknown")
    schedule_scrape(product.id, current_user.id, req_id)
    
    return {"message": "Product retry initiated", "status": "PENDING"}

@router.post("/products/{product_id}/scrape")
@limiter.limit("5/minute")
def trigger_product_scrape(request: Request, product_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id, Product.user_id == current_user.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    product.status = "PENDING"
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        from backend.tracing import get_traced_logger
        logger = get_traced_logger(__name__)
        logger.error(f"Failed to update product status for scrape trigger {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database transaction failed")
        
    from backend.services.task_scheduler import schedule_scrape
    req_id = getattr(request.state, "request_id", "unknown")
    job_id = schedule_scrape(product.id, current_user.id, req_id)
    
    return {"message": "Scrape job triggered for product", "status": "PENDING", "job_id": job_id, "product_id": product_id}


@router.get("/products/{product_id}")
def get_product(product_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id, Product.user_id == current_user.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    snapshots = db.query(PriceSnapshot).filter(PriceSnapshot.product_id == product_id).order_by(PriceSnapshot.timestamp.asc()).all()
    
    is_fake_discount = False
    if snapshots and snapshots[-1].is_fake_discount:
        is_fake_discount = True
        
    from backend.analytics import calculate_statistics, analyze_trend, calculate_deal_score
    statistics = calculate_statistics(snapshots)
    trend = analyze_trend(snapshots)
    deal_score = calculate_deal_score(product, snapshots, is_fake_discount)

    latest = snapshots[-1] if snapshots else None
    prod_dict = {
        "id": product.id,
        "user_id": product.user_id,
        "url": product.url,
        "title": product.title,
        "platform": product.platform,
        "product_id": product.product_id,
        "status": product.status,
        "image_url": product.image_url,
        "brand": product.brand,
        "category": product.category,
        "retry_count": product.retry_count,
        "last_failure": product.last_failure,
        "last_failure_reason": product.last_failure_reason,
        "current_price": latest.price if latest else None,
        "mrp": latest.mrp_shown if latest else None,
    }
        
    return {
        "product": prod_dict,
        "history": snapshots,
        "snapshots": snapshots,
        "is_fake_discount": is_fake_discount,
        "statistics": statistics,
        "trend": trend,
        "deal_score": deal_score
    }

from fastapi.responses import StreamingResponse
import io
import csv

@router.get("/products/{product_id}/export")
def export_product_csv(product_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id, Product.user_id == current_user.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    snapshots = db.query(PriceSnapshot).filter(PriceSnapshot.product_id == product_id).order_by(PriceSnapshot.timestamp.asc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Metadata
    writer.writerow(["Product Name", product.title])
    writer.writerow(["Platform", product.platform.capitalize()])
    writer.writerow(["Product URL", product.url])
    writer.writerow([]) # Blank line
    
    # Headers
    writer.writerow(["Timestamp", "Price", "MRP", "Fake Discount"])
    
    # Data
    for snap in snapshots:
        writer.writerow([
            snap.timestamp.isoformat(),
            snap.price,
            snap.mrp_shown,
            "Yes" if snap.is_fake_discount else "No"
        ])
        
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=product_{product_id}_history.csv"}
    )

from math import ceil

@router.get("/products/search/")
def search_products(
    q: str = "", 
    platform: str = "", 
    category: str = "", 
    page: int = 1, 
    page_size: int = 50, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Product).filter(Product.user_id == current_user.id)
    
    if q:
        query = query.filter(
            (Product.title.ilike(f"%{q}%")) | (Product.brand.ilike(f"%{q}%"))
        )
    if platform:
        query = query.filter(Product.platform == platform)
    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
        
    total_products = query.count()
    total_pages = ceil(total_products / page_size) if total_products > 0 else 1
    
    page = max(1, min(page, total_pages))
    skip = (page - 1) * page_size
    
    products = query.order_by(Product.id.desc()).offset(skip).limit(page_size).all()
    
    product_list = []
    for p in products:
        latest = db.query(PriceSnapshot).filter(PriceSnapshot.product_id == p.id).order_by(PriceSnapshot.timestamp.desc()).first()
        prod_dict = {
            "id": p.id,
            "user_id": p.user_id,
            "url": p.url,
            "title": p.title,
            "platform": p.platform,
            "product_id": p.product_id,
            "status": p.status,
            "image_url": p.image_url,
            "brand": p.brand,
            "category": p.category,
            "retry_count": p.retry_count,
            "last_failure": p.last_failure,
            "last_failure_reason": p.last_failure_reason,
            "current_price": latest.price if latest else None,
            "mrp": latest.mrp_shown if latest else None,
        }
        product_list.append(prod_dict)

    return {
        "products": product_list,
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_products": total_products,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
    }

class AlertCreate(BaseModel):
    threshold_price: float = Field(..., gt=0)
    notification_channel: str = Field(default="whatsapp")
    phone_number: Optional[str] = Field(default=None, min_length=10, max_length=15, pattern=r"^\+?\d+$")
    telegram_chat_id: Optional[str] = Field(default=None, min_length=1, max_length=64)

    @field_validator('notification_channel')
    @classmethod
    def validate_channel(cls, v):
        if v not in SUPPORTED_CHANNELS:
            raise ValueError(f"Unsupported notification channel: '{v}'. Must be one of: {SUPPORTED_CHANNELS}")
        return v

@router.post("/products/{product_id}/alerts")
@limiter.limit(settings.ALERT_RATE_LIMIT)
def create_alert(request: Request, product_id: int, alert: AlertCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.config import settings
    from backend.services.audit_service import log_audit_event
    from backend.tracing import get_traced_logger
    logger = get_traced_logger(__name__)
    
    channel = alert.notification_channel
    
    # Channel-specific destination validation
    if channel == "whatsapp":
        if not alert.phone_number:
            raise HTTPException(status_code=400, detail="phone_number is required for WhatsApp alerts")
        phone_number = alert.phone_number.strip()
        if phone_number.startswith("+"):
            phone_number = f"whatsapp:{phone_number}"
        if not phone_number.startswith("whatsapp:+") or len(phone_number) < 12:
            raise HTTPException(status_code=400, detail="Phone number must start with '+' (e.g. +91...) and include country code")
    elif channel == "telegram":
        if not alert.telegram_chat_id:
            raise HTTPException(status_code=400, detail="telegram_chat_id is required for Telegram alerts")
    
    # Enforce operational alert limit per user
    user_alert_count = db.query(AlertThreshold).filter(AlertThreshold.user_id == current_user.id).count()
    if user_alert_count >= settings.MAX_ALERTS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"Alert limit reached. Maximum allowed price alerts per user is {settings.MAX_ALERTS_PER_USER}."
        )
        
    product = db.query(Product).filter(Product.id == product_id, Product.user_id == current_user.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    new_alert = AlertThreshold(
        user_id=current_user.id,
        product_id=product.id,
        threshold_price=alert.threshold_price,
        notification_channel=channel,
        phone_number=phone_number if channel == "whatsapp" else None,
        telegram_chat_id=alert.telegram_chat_id if channel == "telegram" else None,
        status="ACTIVE"
    )
    
    db.add(new_alert)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create alert for product {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database transaction failed")
        
    db.refresh(new_alert)
    log_audit_event(
        db,
        action="ALERT_CREATED",
        outcome="SUCCESS",
        user_id=current_user.id,
        details={"alert_id": new_alert.id, "product_id": product.id, "threshold": alert.threshold_price, "channel": channel},
        request=request
    )
    
    # Send immediate alert creation confirmation AFTER database commit
    confirmation_sent = False
    try:
        latest_snapshot = db.query(PriceSnapshot).filter(PriceSnapshot.product_id == product.id).order_by(PriceSnapshot.timestamp.desc()).first()
        current_price = latest_snapshot.price if latest_snapshot else None
        
        confirmation_msg = build_alert_confirmation_message(
            product_title=product.title,
            platform=product.platform,
            threshold_price=alert.threshold_price,
            current_price=current_price,
            channel=channel
        )
        
        destination = new_alert.telegram_chat_id if channel == "telegram" else new_alert.phone_number
        notifier = get_notifier(channel)
        confirmation_sent = notifier.send_alert(destination, confirmation_msg)
        if not confirmation_sent:
            logger.warning(f"Confirmation delivery failed or provider unconfigured for {channel} alert {new_alert.id}.")
    except Exception as notify_err:
        logger.warning(f"Failed to send confirmation message for alert {new_alert.id} ({channel}): {notify_err}")

    return {
        "id": new_alert.id,
        "product_id": new_alert.product_id,
        "user_id": new_alert.user_id,
        "phone_number": new_alert.phone_number,
        "threshold_price": new_alert.threshold_price,
        "status": new_alert.status,
        "is_triggered": new_alert.status == "TRIGGERED",
        "notification_channel": new_alert.notification_channel,
        "telegram_chat_id": new_alert.telegram_chat_id,
        "confirmation_sent": confirmation_sent
    }

@router.get("/products/{product_id}/alerts")
def get_alerts(product_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    alerts = db.query(AlertThreshold).filter(AlertThreshold.product_id == product_id, AlertThreshold.user_id == current_user.id).all()
    return [
        {
            "id": a.id,
            "product_id": a.product_id,
            "user_id": a.user_id,
            "phone_number": a.phone_number,
            "threshold_price": a.threshold_price,
            "status": a.status,
            "is_triggered": a.status == "TRIGGERED",
            "notification_channel": getattr(a, 'notification_channel', 'whatsapp') or 'whatsapp',
            "telegram_chat_id": getattr(a, 'telegram_chat_id', None)
        }
        for a in alerts
    ]

class ProductUpdate(BaseModel):
    status: Optional[str] = None

@router.patch("/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product_update: ProductUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id, Product.user_id == current_user.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    if product_update.status:
        if product_update.status not in ["PENDING", "SCRAPING", "SUCCESS", "FAILED", "PAUSED"]:
            raise HTTPException(status_code=400, detail="Invalid product status")
        product.status = product_update.status

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update product")
        
    db.refresh(product)
    return product

@router.delete("/alerts/{alert_id}")
def delete_alert(alert_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    alert = db.query(AlertThreshold).filter(AlertThreshold.id == alert_id, AlertThreshold.user_id == current_user.id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    db.delete(alert)
    db.commit()
    return {"message": "Alert deleted successfully"}


