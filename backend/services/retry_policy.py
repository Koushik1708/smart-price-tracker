import asyncio
import logging

logger = logging.getLogger(__name__)

class RetryPolicy:
    def __init__(self, max_retries: int = 3, base_delay: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        # We might want to differentiate between retryable and non-retryable exceptions
        # in the future, e.g., Network errors vs Validation errors.
        self.retryable_exceptions = (Exception,)
        self.non_retryable_exceptions = (ValueError, TypeError)

    def exponential_backoff(self, retry_count: int) -> float:
        """Returns the delay in seconds for the next retry."""
        return self.base_delay * (2 ** retry_count)

    def should_retry(self, exception: Exception, current_retry_count: int) -> bool:
        if current_retry_count >= self.max_retries:
            return False
            
        if isinstance(exception, self.non_retryable_exceptions):
            return False
            
        if isinstance(exception, self.retryable_exceptions):
            return True
            
        return False
