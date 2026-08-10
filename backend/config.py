import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

class Settings:
    # API & App Settings
    API_VERSION = os.getenv("API_VERSION", "2.3.0")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "")
    
    # Timeouts & Limits
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
    SCRAPER_TIMEOUT = int(os.getenv("SCRAPER_TIMEOUT", "60000")) # ms
    PLAYWRIGHT_TIMEOUT = int(os.getenv("PLAYWRIGHT_TIMEOUT", "60000")) # ms
    DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
    MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", "100"))
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./price_tracker.db")
    
    # Auth
    JWT_SECRET = os.getenv("JWT_SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    
    # Twilio (Optional)
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
    
    # Telegram (Optional)
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_DEFAULT_CHAT_ID = os.getenv("TELEGRAM_DEFAULT_CHAT_ID")
    
    # Celery & Queue
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or os.getenv("UPSTASH_REDIS_URL") or "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND") or os.getenv("REDIS_URL") or os.getenv("UPSTASH_REDIS_URL") or "redis://localhost:6379/0"
    CELERY_CONCURRENCY = int(os.getenv("CELERY_CONCURRENCY", "4"))
    QUEUE_NAME = os.getenv("QUEUE_NAME", "scraper_queue")
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    
    # Operational Limits & Security Controls
    MAX_PRODUCTS_PER_USER = int(os.getenv("MAX_PRODUCTS_PER_USER", "50"))
    MAX_ALERTS_PER_USER = int(os.getenv("MAX_ALERTS_PER_USER", "20"))
    QUEUE_SIZE_LIMIT = int(os.getenv("QUEUE_SIZE_LIMIT", "1000"))
    MAX_CONCURRENT_SCRAPE_JOBS = int(os.getenv("MAX_CONCURRENT_SCRAPE_JOBS", "10"))
    
    # Brute Force Protection & Lockout
    ACCOUNT_LOCKOUT_ATTEMPTS = int(os.getenv("ACCOUNT_LOCKOUT_ATTEMPTS", "5"))
    ACCOUNT_LOCKOUT_DURATION_MINUTES = int(os.getenv("ACCOUNT_LOCKOUT_DURATION_MINUTES", "15"))
    
    # API Rate Limiting Config
    LOGIN_RATE_LIMIT = os.getenv("LOGIN_RATE_LIMIT", "5/minute")
    REGISTER_RATE_LIMIT = os.getenv("REGISTER_RATE_LIMIT", "5/minute")
    TRACK_RATE_LIMIT = os.getenv("TRACK_RATE_LIMIT", "10/minute")
    ALERT_RATE_LIMIT = os.getenv("ALERT_RATE_LIMIT", "5/minute")
    
    @classmethod
    def validate(cls):
        # Fail fast if critical variables are missing
        if not cls.JWT_SECRET:
            raise ValueError("JWT_SECRET_KEY is required but not set.")
        if cls.ENVIRONMENT == "production" and (not cls.JWT_SECRET or len(cls.JWT_SECRET) < 32):
            raise ValueError("JWT_SECRET_KEY must be a strong secret (at least 32 characters) in production.")
        # We don't fail for Twilio as it's optional

settings = Settings()
settings.validate()
import time
settings.START_TIME = time.time()
