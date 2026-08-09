#!/bin/bash
set -e

echo "Starting Celery worker in background..."
python -m celery -A backend.celery_app:celery_app worker --loglevel=info -Q scraper_queue --pool=solo -c 1 &
WORKER_PID=$!

# Brief pause to verify background worker process didn't exit immediately on startup failure
sleep 5
if ! kill -0 $WORKER_PID 2>/dev/null; then
    echo "ERROR: Celery worker process failed to start."
    exit 1
fi

echo "Celery worker process running with PID $WORKER_PID."
echo "Starting FastAPI web server in foreground..."

exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
