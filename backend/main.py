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

# Setup ContextVar for Request ID
request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Load env
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Structured Logging Setup
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        req_id = request_id_ctx_var.get()
        if req_id:
            log_obj["request_id"] = req_id
            
        if hasattr(record, "product_id"):
            log_obj["product_id"] = record.product_id
        if hasattr(record, "platform"):
            log_obj["platform"] = record.platform
        if hasattr(record, "url"):
            log_obj["url"] = record.url
        if hasattr(record, "status"):
            log_obj["status"] = record.status
        if hasattr(record, "processing_time"):
            log_obj["processing_time"] = record.processing_time
        if hasattr(record, "error_reason"):
            log_obj["error_reason"] = record.error_reason

        return json.dumps(log_obj)

log_handler = logging.StreamHandler(sys.stdout)
log_handler.setFormatter(JSONFormatter())
logging.basicConfig(level=logging.INFO, handlers=[log_handler])
logger = logging.getLogger(__name__)

# Environment Validation
if not os.getenv("DATABASE_URL"):
    logger.warning("DATABASE_URL is not set. Falling back to local SQLite.")

optional_vars = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_NUMBER", "TARGET_WHATSAPP_NUMBER", "FRONTEND_URL"]
for var in optional_vars:
    if not os.getenv(var):
        logger.warning(f"Optional environment variable {var} is missing. Some features may be degraded.")

# SlowAPI Setup
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# Async IO Policy
if sys.platform == "win32" and sys.version_info < (3, 8):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Price Tracker & Fake Discount MVP")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Configuration
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
else:
    origins = ["http://localhost:5173"]

if FRONTEND_URL and FRONTEND_URL not in origins:
    origins.append(FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID Middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    req_id = str(uuid.uuid4())
    request_id_ctx_var.set(req_id)
    request.state.request_id = req_id
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    response.headers["X-Request-ID"] = req_id
    logger.info(f"{request.method} {request.url.path} completed", extra={"processing_time": f"{process_time:.4f}s", "status": response.status_code})
    return response

# Centralized Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": str(exc.detail), "error_code": "HTTP_ERROR"}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"success": False, "message": "Validation Error", "details": exc.errors(), "error_code": "VALIDATION_ERROR"}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True, extra={"request_id": error_id})
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Internal Server Error", "error_code": "INTERNAL_ERROR", "debug": str(exc)}
    )

from backend.api_routes import router
app.include_router(router)

@app.get("/")
def read_root():
    return {"status": "ok"}
