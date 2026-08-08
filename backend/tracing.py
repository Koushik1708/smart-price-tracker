import os
import sys
import uuid
import json
import socket
import logging
from contextvars import ContextVar
from typing import Optional, Dict, Any

# ---------------------------------------------------------
# Distributed Tracing Context Variables
# ---------------------------------------------------------

ctx_trace_id: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
ctx_span_id: ContextVar[Optional[str]] = ContextVar("span_id", default=None)
ctx_parent_span_id: ContextVar[Optional[str]] = ContextVar("parent_span_id", default=None)
ctx_span_name: ContextVar[Optional[str]] = ContextVar("span_name", default=None)

ctx_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
ctx_job_id: ContextVar[Optional[str]] = ContextVar("job_id", default=None)
ctx_job_type: ContextVar[Optional[str]] = ContextVar("job_type", default=None)
ctx_user_id: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
ctx_product_id: ContextVar[Optional[str]] = ContextVar("product_id", default=None)

ctx_attempt: ContextVar[Optional[int]] = ContextVar("attempt", default=None)
ctx_max_attempts: ContextVar[Optional[int]] = ContextVar("max_attempts", default=None)

ctx_queue_time_ms: ContextVar[Optional[int]] = ContextVar("queue_time_ms", default=None)
ctx_execution_time_ms: ContextVar[Optional[int]] = ContextVar("execution_time_ms", default=None)

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------

def start_trace(request_id: str) -> str:
    """Starts a new trace, generating a trace_id. Call exactly once per HTTP request."""
    trace_id = str(uuid.uuid4())
    ctx_trace_id.set(trace_id)
    ctx_request_id.set(request_id)
    return trace_id

def start_span(span_name: str) -> str:
    """Starts a new execution span, setting the previous span_id as parent."""
    new_span_id = str(uuid.uuid4())
    current_span = ctx_span_id.get()
    
    ctx_parent_span_id.set(current_span)
    ctx_span_id.set(new_span_id)
    ctx_span_name.set(span_name)
    
    return new_span_id

def end_span(previous_span_id: Optional[str] = None, previous_parent_id: Optional[str] = None, previous_span_name: Optional[str] = None):
    """Restores the context to the previous span (useful for synchronous sequential spans)."""
    ctx_span_id.set(previous_span_id)
    ctx_parent_span_id.set(previous_parent_id)
    ctx_span_name.set(previous_span_name)

def set_context(**kwargs):
    """Dynamically set any context variables."""
    if "trace_id" in kwargs: ctx_trace_id.set(kwargs["trace_id"])
    if "span_id" in kwargs: ctx_span_id.set(kwargs["span_id"])
    if "parent_span_id" in kwargs: ctx_parent_span_id.set(kwargs["parent_span_id"])
    if "span_name" in kwargs: ctx_span_name.set(kwargs["span_name"])
    if "request_id" in kwargs: ctx_request_id.set(kwargs["request_id"])
    if "job_id" in kwargs: ctx_job_id.set(kwargs["job_id"])
    if "job_type" in kwargs: ctx_job_type.set(kwargs["job_type"])
    if "user_id" in kwargs: ctx_user_id.set(str(kwargs["user_id"]))
    if "product_id" in kwargs: ctx_product_id.set(str(kwargs["product_id"]))
    if "attempt" in kwargs: ctx_attempt.set(kwargs["attempt"])
    if "max_attempts" in kwargs: ctx_max_attempts.set(kwargs["max_attempts"])
    if "queue_time_ms" in kwargs: ctx_queue_time_ms.set(kwargs["queue_time_ms"])
    if "execution_time_ms" in kwargs: ctx_execution_time_ms.set(kwargs["execution_time_ms"])

def clear_context():
    """Clears all tracing context variables."""
    ctx_trace_id.set(None)
    ctx_span_id.set(None)
    ctx_parent_span_id.set(None)
    ctx_span_name.set(None)
    ctx_request_id.set(None)
    ctx_job_id.set(None)
    ctx_job_type.set(None)
    ctx_user_id.set(None)
    ctx_product_id.set(None)
    ctx_attempt.set(None)
    ctx_max_attempts.set(None)
    ctx_queue_time_ms.set(None)
    ctx_execution_time_ms.set(None)

# ---------------------------------------------------------
# Universal Logging Formatter
# ---------------------------------------------------------

# Cache standard values
WORKER_HOSTNAME = socket.gethostname()
WORKER_PID = os.getpid()

class TracedJSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "service_name": os.getenv("SERVICE_NAME", "letsgo_backend"),
            "service_version": os.getenv("APP_VERSION", "1.0.0"),
            "environment": os.getenv("ENVIRONMENT", "development"),
            "worker_hostname": WORKER_HOSTNAME,
            "worker_pid": WORKER_PID
        }
        
        # Inject context variables (always output the fields as requested, using null if missing)
        log_obj["trace_id"] = ctx_trace_id.get()
        log_obj["span_id"] = ctx_span_id.get()
        log_obj["parent_span_id"] = ctx_parent_span_id.get()
        log_obj["span_name"] = ctx_span_name.get()
        log_obj["request_id"] = ctx_request_id.get()
        log_obj["job_id"] = ctx_job_id.get()
        log_obj["job_type"] = ctx_job_type.get()
        
        user_id = ctx_user_id.get()
        if user_id: log_obj["user_id"] = user_id
            
        product_id = ctx_product_id.get()
        if product_id: log_obj["product_id"] = product_id
            
        log_obj["attempt"] = ctx_attempt.get()
        log_obj["max_attempts"] = ctx_max_attempts.get()
        log_obj["queue_time_ms"] = ctx_queue_time_ms.get()
        log_obj["execution_time_ms"] = ctx_execution_time_ms.get()

        # Inject extra attributes passed explicitly via logger(..., extra={})
        # Overrides ContextVars if conflicts occur (e.g., event, status)
        for key in ["event", "status", "platform", "url", "error_reason", "queue_time_ms", "execution_time_ms"]:
            if hasattr(record, key):
                log_obj[key] = getattr(record, key)

        return json.dumps(log_obj)

def get_traced_logger(name: str) -> logging.Logger:
    """Helper to get a logger configured with TracedJSONFormatter."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(TracedJSONFormatter())
        logger.addHandler(handler)
    logger.propagate = False
    return logger
