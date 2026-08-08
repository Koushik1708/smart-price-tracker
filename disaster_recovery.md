# Disaster Recovery & Operations Documentation

This document outlines the operational procedures for backup, recovery, and failover management of the Price Tracker system.

## 1. Database Backup Strategy (SQLite)

The system uses SQLite in WAL (Write-Ahead Logging) mode for concurrent access and resilience. Standard file copies of WAL databases can lead to corrupt copies.

### Hot Backups
We use the SQLite `backup` API to run online backups while the backend is active. The script is located at:
`scripts/backup_db.py`

### Cron/Automation
To run backups daily, add a cron job on the host machine:
```bash
0 2 * * * /app/venv/bin/python /app/scripts/backup_db.py
```
Backups are saved under the `backups/` directory.

### Restore Procedure
To restore the database:
1. Stop the FastAPI and Celery worker services.
2. Back up the active corrupted file (if any):
   ```bash
   mv price_tracker.db price_tracker.db.corrupt
   ```
3. Copy the latest backup file to the target name:
   ```bash
   cp backups/price_tracker_backup_YYYYMMDD_HHMMSS.db price_tracker.db
   ```
4. Start backend and Celery worker.

---

## 2. Redis Persistence Strategy

Redis is used as the Celery task broker and results backend. Under production, Redis is configured in `docker-compose.prod.yml` with:
- **Append Only File (AOF)** enabled (`--appendonly yes`) for durability.
- **RDB Snapshots** enabled for point-in-time recovery.

If the Redis container crashes:
1. Docker Compose restarts it automatically.
2. Redis reads the `appendonly.aof` file from the mounted `redis_data` volume to restore the exact state of the task queue.

---

## 3. Disaster Recovery Scenarios

### Worker Crash Recovery
If a worker crashes mid-task:
- Tasks marked with `acks_late=True` will not be lost.
- Upon worker restart, Celery will automatically fetch the unacknowledged messages and retry them.

### Poison Job Detection
- Persistent failures are logged under `event="job_dead_letter"` and pushed to the Redis list `celery_dead_letter_queue`.
- Run the following command to inspect poison jobs:
  ```bash
  redis-cli LRANGE celery_dead_letter_queue 0 -1
  ```
