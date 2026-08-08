import os
import sys
import psutil
import shutil
import time
import datetime
from math import ceil
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.database import get_db
from backend.models import User, Product, PriceSnapshot, AlertThreshold, AuditLog
from backend.auth import get_current_admin_user
from backend.services.audit_service import log_audit_event
from backend.services.task_scheduler import schedule_scrape
from backend.metrics import ADMIN_ACTIONS_TOTAL
from backend.config import settings

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin_user)])

# Helper for masking secrets
def mask_secret(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    if len(value) <= 6:
        return "******"
    return value[:3] + "..." + value[-3:]

# ---------------------------------------------------------
# User Management
# ---------------------------------------------------------

@router.get("/users")
def get_admin_users(
    q: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(User)
    if q:
        query = query.filter((User.name.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%")))
        
    total_users = query.count()
    total_pages = ceil(total_users / page_size) if total_users > 0 else 1
    page = min(page, total_pages)
    skip = (page - 1) * page_size
    
    users = query.order_by(User.id.desc()).offset(skip).limit(page_size).all()
    
    result = []
    for u in users:
        prod_count = db.query(Product).filter(Product.user_id == u.id).count()
        alert_count = db.query(AlertThreshold).filter(AlertThreshold.user_id == u.id).count()
        result.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "is_admin": u.is_admin,
            "failed_login_attempts": u.failed_login_attempts,
            "locked_until": u.locked_until,
            "created_at": u.created_at,
            "product_count": prod_count,
            "alert_count": alert_count
        })
        
    return {
        "users": result,
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_users": total_users,
            "total_pages": total_pages
        }
    }

@router.post("/users/{user_id}/role")
def toggle_user_role(
    user_id: int,
    request: Request,
    is_admin: bool = Query(...),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    target_user.is_admin = is_admin
    db.commit()
    
    ADMIN_ACTIONS_TOTAL.labels(action="toggle_user_role").inc()
    log_audit_event(
        db,
        action="ADMIN_ACTION",
        outcome="SUCCESS",
        user_id=admin_user.id,
        details={"target_user_id": user_id, "new_is_admin": is_admin},
        request=request
    )
    return {"message": f"Updated user {user_id} admin status to {is_admin}"}

# ---------------------------------------------------------
# Global Product & Scrape Management
# ---------------------------------------------------------

@router.get("/products")
def get_admin_products(
    q: str = "",
    status_filter: str = "",
    platform_filter: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Product)
    if q:
        query = query.filter((Product.title.ilike(f"%{q}%")) | (Product.brand.ilike(f"%{q}%")))
    if status_filter:
        query = query.filter(Product.status == status_filter)
    if platform_filter:
        query = query.filter(Product.platform == platform_filter)
        
    total_products = query.count()
    total_pages = ceil(total_products / page_size) if total_products > 0 else 1
    page = min(page, total_pages)
    skip = (page - 1) * page_size
    
    products = query.order_by(Product.id.desc()).offset(skip).limit(page_size).all()
    
    return {
        "products": products,
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_products": total_products,
            "total_pages": total_pages
        }
    }

@router.post("/products/{product_id}/retry")
def admin_retry_product(
    product_id: int,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    product.status = "PENDING"
    product.retry_count = 0
    db.commit()
    
    req_id = getattr(request.state, "request_id", "unknown")
    schedule_scrape(product.id, product.user_id, req_id)
    
    ADMIN_ACTIONS_TOTAL.labels(action="force_retry_product").inc()
    log_audit_event(
        db,
        action="ADMIN_ACTION",
        outcome="SUCCESS",
        user_id=admin_user.id,
        details={"product_id": product_id, "action_type": "force_retry"},
        request=request
    )
    return {"message": "Product scrape retry queued", "product_id": product_id}

@router.delete("/products/{product_id}")
def admin_delete_product(
    product_id: int,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    db.delete(product)
    db.commit()
    
    ADMIN_ACTIONS_TOTAL.labels(action="admin_delete_product").inc()
    log_audit_event(
        db,
        action="ADMIN_ACTION",
        outcome="SUCCESS",
        user_id=admin_user.id,
        details={"product_id": product_id, "action_type": "delete"},
        request=request
    )
    return {"message": "Product deleted successfully"}

# ---------------------------------------------------------
# Alerts & DLQ Viewer
# ---------------------------------------------------------

@router.get("/alerts")
def get_admin_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(AlertThreshold)
    total_alerts = query.count()
    total_pages = ceil(total_alerts / page_size) if total_alerts > 0 else 1
    page = min(page, total_pages)
    skip = (page - 1) * page_size
    
    alerts = query.order_by(AlertThreshold.id.desc()).offset(skip).limit(page_size).all()
    return {
        "alerts": alerts,
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_alerts": total_alerts,
            "total_pages": total_pages
        }
    }

@router.get("/failed-jobs")
def get_failed_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """View failed scrape jobs and Dead Letter Queue items."""
    query = db.query(Product).filter(Product.status == "FAILED")
    total_failed = query.count()
    total_pages = ceil(total_failed / page_size) if total_failed > 0 else 1
    page = min(page, total_pages)
    skip = (page - 1) * page_size
    
    failed_products = query.order_by(Product.last_failure.desc().nullslast()).offset(skip).limit(page_size).all()
    
    return {
        "failed_jobs": [
            {
                "id": p.id,
                "user_id": p.user_id,
                "title": p.title,
                "url": p.url,
                "platform": p.platform,
                "retry_count": p.retry_count,
                "last_failure": p.last_failure,
                "last_failure_reason": p.last_failure_reason
            }
            for p in failed_products
        ],
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_failed": total_failed,
            "total_pages": total_pages
        }
    }

# ---------------------------------------------------------
# Worker, Queue, Redis & Celery Status
# ---------------------------------------------------------

@router.get("/redis")
def get_redis_status():
    import redis
    try:
        r = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2)
        r.ping()
        info = r.info()
        return {
            "status": "connected",
            "redis_version": info.get("redis_version"),
            "used_memory_human": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "uptime_in_seconds": info.get("uptime_in_seconds")
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@router.get("/queues")
def get_queue_status():
    import redis
    try:
        r = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2)
        depth = r.llen(settings.QUEUE_NAME)
        return {
            "queue_name": settings.QUEUE_NAME,
            "depth": depth,
            "queue_limit": settings.QUEUE_SIZE_LIMIT,
            "status": "healthy" if depth < settings.QUEUE_SIZE_LIMIT else "congested"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@router.get("/workers")
@router.get("/celery")
def get_worker_status():
    import redis
    try:
        r = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2)
        queue_len = r.llen(settings.QUEUE_NAME)
        return {
            "status": "online",
            "queue_name": settings.QUEUE_NAME,
            "queue_depth": queue_len,
            "concurrency": settings.CELERY_CONCURRENCY,
            "max_retries": settings.MAX_RETRIES
        }
    except Exception as e:
        return {"status": "offline", "error": str(e)}

# ---------------------------------------------------------
# System Diagnostics & Configuration Viewer
# ---------------------------------------------------------

@router.get("/diagnostics")
def get_system_diagnostics(db: Session = Depends(get_db)):
    mem = psutil.virtual_memory()
    total_disk, used_disk, free_disk = shutil.disk_usage("/")
    
    # DB test
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"
        
    return {
        "python_version": sys.version,
        "platform": sys.platform,
        "uptime_seconds": int(time.time() - settings.START_TIME),
        "cpu": {
            "percent": psutil.cpu_percent(interval=None),
            "count": psutil.cpu_count()
        },
        "memory": {
            "total_mb": round(mem.total / (2**20), 2),
            "available_mb": round(mem.available / (2**20), 2),
            "percent": mem.percent
        },
        "disk": {
            "total_gb": round(total_disk / (2**30), 2),
            "free_gb": round(free_disk / (2**30), 2),
            "free_percent": round((free_disk / total_disk) * 100, 2)
        },
        "database": db_status
    }

@router.get("/config")
def get_runtime_config():
    return {
        "API_VERSION": settings.API_VERSION,
        "ENVIRONMENT": settings.ENVIRONMENT,
        "FRONTEND_URL": settings.FRONTEND_URL,
        "ALLOWED_ORIGINS": settings.ALLOWED_ORIGINS,
        "DATABASE_URL": mask_secret(settings.DATABASE_URL),
        "JWT_SECRET": mask_secret(settings.JWT_SECRET),
        "CELERY_BROKER_URL": mask_secret(settings.CELERY_BROKER_URL),
        "TWILIO_ACCOUNT_SID": mask_secret(settings.TWILIO_ACCOUNT_SID),
        "MAX_PRODUCTS_PER_USER": settings.MAX_PRODUCTS_PER_USER,
        "MAX_ALERTS_PER_USER": settings.MAX_ALERTS_PER_USER,
        "QUEUE_SIZE_LIMIT": settings.QUEUE_SIZE_LIMIT,
        "MAX_CONCURRENT_SCRAPE_JOBS": settings.MAX_CONCURRENT_SCRAPE_JOBS,
        "ACCOUNT_LOCKOUT_ATTEMPTS": settings.ACCOUNT_LOCKOUT_ATTEMPTS,
        "ACCOUNT_LOCKOUT_DURATION_MINUTES": settings.ACCOUNT_LOCKOUT_DURATION_MINUTES,
        "LOGIN_RATE_LIMIT": settings.LOGIN_RATE_LIMIT,
        "TRACK_RATE_LIMIT": settings.TRACK_RATE_LIMIT
    }

@router.get("/stats")
def get_system_stats(db: Session = Depends(get_db)):
    total_users = db.query(User).count()
    total_products = db.query(Product).count()
    total_snapshots = db.query(PriceSnapshot).count()
    total_alerts = db.query(AlertThreshold).count()
    active_alerts = db.query(AlertThreshold).filter(AlertThreshold.status == "ACTIVE").count()
    failed_products = db.query(Product).filter(Product.status == "FAILED").count()
    successful_products = db.query(Product).filter(Product.status == "SUCCESS").count()
    
    return {
        "total_users": total_users,
        "total_products": total_products,
        "total_snapshots": total_snapshots,
        "total_alerts": total_alerts,
        "active_alerts": active_alerts,
        "successful_products": successful_products,
        "failed_products": failed_products
    }

# ---------------------------------------------------------
# Audit Log Viewer
# ---------------------------------------------------------

@router.get("/audit-logs")
def get_audit_logs(
    action: str = "",
    user_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)
        
    total_logs = query.count()
    total_pages = ceil(total_logs / page_size) if total_logs > 0 else 1
    page = min(page, total_pages)
    skip = (page - 1) * page_size
    
    logs = query.order_by(AuditLog.id.desc()).offset(skip).limit(page_size).all()
    
    return {
        "audit_logs": logs,
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_logs": total_logs,
            "total_pages": total_pages
        }
    }
