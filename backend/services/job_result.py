from pydantic import BaseModel, Field
from typing import Optional
import datetime
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"

class JobResult(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.PENDING
    started_at: Optional[datetime.datetime] = None
    finished_at: Optional[datetime.datetime] = None
    execution_time: Optional[float] = None
    retry_count: int = 0
    error: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[int] = None
    product_id: Optional[int] = None
