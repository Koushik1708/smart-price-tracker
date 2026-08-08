import json
import datetime
from typing import Optional, Dict, Any, Union
from fastapi import Request
from sqlalchemy.orm import Session
from backend.models import AuditLog
from backend.tracing import (
    get_traced_logger,
    ctx_trace_id,
    ctx_span_id,
    ctx_request_id,
    ctx_user_id
)
from backend.metrics import AUDIT_EVENTS_TOTAL

logger = get_traced_logger(__name__)

SENSITIVE_KEYS = {"password", "password_hash", "jwt", "token", "access_token", "secret", "auth_token"}

def sanitize_details(details: Union[Dict[str, Any], str, None]) -> Optional[str]:
    """Converts details to string while redacting sensitive fields."""
    if details is None:
        return None
    if isinstance(details, str):
        return details
    if isinstance(details, dict):
        sanitized = {}
        for key, value in details.items():
            if any(s in key.lower() for s in SENSITIVE_KEYS):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return json.dumps(sanitized)
    return str(details)

def log_audit_event(
    db: Session,
    action: str,
    outcome: str,
    user_id: Optional[int] = None,
    details: Optional[Union[Dict[str, Any], str]] = None,
    request: Optional[Request] = None
) -> AuditLog:
    """
    Creates an immutable AuditLog entry in the database, emits a structured log,
    and updates Prometheus metrics.
    """
    # Trace identifiers
    trace_id = ctx_trace_id.get()
    span_id = ctx_span_id.get()
    req_id = ctx_request_id.get()

    if request:
        if not req_id:
            req_id = getattr(request.state, "request_id", None)
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
    else:
        ip_address = "internal"
        user_agent = "internal"

    if user_id is None:
        ctx_uid = ctx_user_id.get()
        if ctx_uid and ctx_uid.isdigit():
            user_id = int(ctx_uid)

    clean_details = sanitize_details(details)

    audit_entry = AuditLog(
        trace_id=trace_id,
        span_id=span_id,
        request_id=req_id,
        user_id=user_id,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        action=action,
        outcome=outcome,
        ip_address=ip_address,
        user_agent=user_agent,
        details=clean_details
    )

    try:
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to persist AuditLog to database: {e}", exc_info=True)

    # Metric & Log output
    try:
        AUDIT_EVENTS_TOTAL.labels(action=action, outcome=outcome).inc()
    except Exception:
        pass

    logger.info(
        f"AUDIT EVENT: {action} ({outcome})",
        extra={
            "event": "audit_log",
            "action": action,
            "outcome": outcome,
            "user_id": str(user_id) if user_id else None,
            "ip_address": ip_address
        }
    )

    return audit_entry
