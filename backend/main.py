from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from backend.database import engine, Base
import sys
import asyncio
import os
import uuid
import logging
import json
import time
from dotenv import load_dotenv
from contextvars import ContextVar
from backend.config import settings

from backend.tracing import get_traced_logger, start_trace, start_span, end_span, clear_context

logger = get_traced_logger(__name__)

# Environment Validation
if not settings.DATABASE_URL:
    logger.warning("DATABASE_URL is not set. Falling back to local SQLite.")

if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
    logger.warning("Optional Twilio environment variables are missing. Some features may be degraded.")

# Main FastAPI Application Setup - Auth updated case-insensitive
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# Async IO Policy
if sys.platform == "win32" and sys.version_info < (3, 8):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Price History & Fake-Discount Tracker Enterprise API",
    description="Enterprise-grade pricing tracker, fake-discount detector, and administrative governance system.",
    version=settings.API_VERSION,
    openapi_tags=[
        {"name": "auth", "description": "Authentication and Identity Management"},
        {"name": "dashboard", "description": "User Dashboard Analytics and Metrics"},
        {"name": "products", "description": "Product Tracking, Snapshots, and CSV Exports"},
        {"name": "alerts", "description": "WhatsApp Price Drop Alerts"},
        {"name": "admin", "description": "Enterprise Administration, System Diagnostics, and Audit Logging"},
    ]
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler) # type: ignore

# CORS Configuration
if settings.ALLOWED_ORIGINS:
    origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
else:
    origins = ["http://localhost:5173"]

if settings.FRONTEND_URL and settings.FRONTEND_URL not in origins:
    origins.append(settings.FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers Middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self' http: https: data: 'unsafe-inline' 'unsafe-eval';"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Request ID Middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    req_id = str(uuid.uuid4())
    trace_id = start_trace(req_id)
    start_span("API")
    request.state.request_id = req_id
    
    is_metrics_path = request.url.path in ["/metrics/prometheus", "/internal/metrics"]
    
    start_time = time.perf_counter()
    try:
        if not is_metrics_path:
            logger.info(f"Request received: {request.method} {request.url.path}", extra={"event": "request_received"})
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Trace-ID"] = trace_id or ""
        
        if not is_metrics_path:
            logger.info(f"{request.method} {request.url.path} completed", extra={"execution_time_ms": int(process_time * 1000), "status": response.status_code})
            try:
                from backend.metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_LATENCY
                HTTP_REQUESTS_TOTAL.labels(method=request.method, endpoint=request.url.path, status=response.status_code).inc()
                HTTP_REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(process_time)
            except Exception as e:
                logger.warning(f"Failed to record Prometheus metrics: {e}")
                
        return response
    finally:
        clear_context()

# Centralized Exception Handlers
import datetime

def build_error_response(request: Request, status_code: int, message: str, error_code: str, details=None):
    req_id = getattr(request.state, "request_id", "unknown")
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": message,
            "error_code": error_code,
            "error": {
                "code": error_code,
                "message": message,
                "details": details
            },
            "request_id": req_id,
            "timestamp": timestamp
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return build_error_response(request, exc.status_code, exc.detail, "HTTP_ERROR")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    try:
        from backend.metrics import EXCEPTION_COUNTER
        EXCEPTION_COUNTER.labels(exception_type="ValidationError").inc()
    except Exception:
        pass
    return build_error_response(request, 422, "Validation Error", "VALIDATION_ERROR", exc.errors())

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True, extra={"request_id": error_id})
    
    try:
        from backend.metrics import EXCEPTION_COUNTER
        from sqlalchemy.exc import SQLAlchemyError
        from redis.exceptions import RedisError
        
        if isinstance(exc, SQLAlchemyError):
            EXCEPTION_COUNTER.labels(exception_type="DatabaseError").inc()
        elif isinstance(exc, RedisError):
            EXCEPTION_COUNTER.labels(exception_type="RedisError").inc()
        elif isinstance(exc, (asyncio.TimeoutError, TimeoutError)) or "timeout" in str(exc).lower():
            EXCEPTION_COUNTER.labels(exception_type="TimeoutError").inc()
        else:
            exc_name = type(exc).__name__
            if "twilio" in exc_name.lower():
                EXCEPTION_COUNTER.labels(exception_type="TwilioError").inc()
            elif "playwright" in exc_name.lower():
                EXCEPTION_COUNTER.labels(exception_type="PlaywrightError").inc()
            else:
                EXCEPTION_COUNTER.labels(exception_type="UnknownError").inc()
    except Exception:
        pass
        
    return build_error_response(request, 500, "Internal Server Error", "INTERNAL_ERROR", str(exc))

from backend.api_routes import router as api_router
from backend.auth_routes import router as auth_router
from backend.dashboard_routes import router as dashboard_router
from backend.admin_routes import router as admin_router
app.include_router(auth_router)
app.include_router(api_router)
app.include_router(dashboard_router)
app.include_router(admin_router)

from fastapi import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

@app.get("/metrics/prometheus")
@app.get("/internal/metrics")
def get_prometheus_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/")
def read_root():
    return {"status": "ok"}
