from prometheus_client import Counter, Histogram, Gauge

# HTTP Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"]
)

HTTP_REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"]
)

# Celery metrics
CELERY_QUEUE_DEPTH = Gauge(
    "celery_queue_depth",
    "Current celery queue depth",
    ["queue"]
)

CELERY_QUEUE_WAIT_TIME = Histogram(
    "celery_queue_wait_seconds",
    "Time jobs spend waiting in the queue in seconds"
)

CELERY_WORKER_EXECUTION_TIME = Histogram(
    "celery_worker_execution_seconds",
    "Celery task execution duration in seconds",
    ["job_type"]
)

CELERY_JOBS_COMPLETED = Counter(
    "celery_jobs_completed_total",
    "Total completed celery jobs",
    ["job_type", "status"]
)

# Structured exception counters
EXCEPTION_COUNTER = Counter(
    "app_exceptions_total",
    "Structured application exceptions count",
    ["exception_type"]  # DatabaseError, RedisError, PlaywrightError, TimeoutError, ValidationError, TwilioError, UnknownError
)

# Phase 6 Security & Admin Metrics
AUTH_FAILURES_TOTAL = Counter(
    "auth_failures_total",
    "Total authentication failures",
    ["reason"]
)

ADMIN_ACTIONS_TOTAL = Counter(
    "admin_actions_total",
    "Total administrative actions executed",
    ["action"]
)

AUDIT_EVENTS_TOTAL = Counter(
    "audit_events_total",
    "Total audit log events recorded",
    ["action", "outcome"]
)

