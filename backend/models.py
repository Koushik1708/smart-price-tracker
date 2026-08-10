from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.orm import relationship
import datetime
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    is_admin = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)

    products = relationship("Product", back_populates="user", cascade="all, delete-orphan")
    alert_thresholds = relationship("AlertThreshold", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    notification_preference = relationship("NotificationPreference", uselist=False, back_populates="user", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    url = Column(String, index=True)
    title = Column(String)
    platform = Column(String, index=True) # 'amazon' or 'flipkart'
    product_id = Column(String, index=True) # ID from the platform
    status = Column(String, default="PENDING", index=True)
    
    image_url = Column(String, nullable=True)
    brand = Column(String, nullable=True, index=True)
    category = Column(String, nullable=True, index=True)
    
    retry_count = Column(Integer, default=0)
    last_failure = Column(DateTime, nullable=True)
    last_failure_reason = Column(String, nullable=True)
    
    __table_args__ = (
        UniqueConstraint("user_id", "url", name="ix_products_user_url"),
        Index("ix_products_user_status", "user_id", "status"),
    )
    
    price_snapshots = relationship("PriceSnapshot", back_populates="product", cascade="all, delete-orphan")
    alert_thresholds = relationship("AlertThreshold", back_populates="product")
    user = relationship("User", back_populates="products")

class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    price = Column(Float)
    mrp_shown = Column(Float)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), index=True)
    is_fake_discount = Column(Boolean, default=False)
    
    __table_args__ = (
        CheckConstraint('price > 0', name='check_price_positive'),
        CheckConstraint('mrp_shown > 0', name='check_mrp_positive'),
        Index("ix_price_snapshots_product_time", "product_id", "timestamp"),
    )

    product = relationship("Product", back_populates="price_snapshots")

class AlertThreshold(Base):
    __tablename__ = "alert_thresholds"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    phone_number = Column(String) # For WhatsApp
    threshold_price = Column(Float)
    status = Column(String, default="ACTIVE", index=True) # ACTIVE, TRIGGERED, FAILED
    notification_channel = Column(String, default="whatsapp", index=True) # whatsapp, telegram
    telegram_chat_id = Column(String, nullable=True)

    product = relationship("Product", back_populates="alert_thresholds")
    user = relationship("User", back_populates="alert_thresholds")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String, index=True, nullable=True)
    span_id = Column(String, nullable=True)
    request_id = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), index=True)
    action = Column(String, index=True) # LOGIN, LOGOUT, PRODUCT_TRACKED, PRODUCT_DELETED, ALERT_CREATED, ADMIN_ACTION, SECURITY_EVENT, FAILED_LOGIN
    outcome = Column(String, index=True) # SUCCESS, FAILURE, BLOCKED
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    details = Column(String, nullable=True)

    user = relationship("User", back_populates="audit_logs")

class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True, nullable=False)
    whatsapp_phone_number = Column(String, nullable=True)
    telegram_chat_id = Column(String, nullable=True)
    telegram_username = Column(String, nullable=True)
    telegram_connected_at = Column(DateTime, nullable=True)
    default_notification_channel = Column(String, default="whatsapp")
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))

    user = relationship("User", back_populates="notification_preference")

class TelegramConnectCode(Base):
    __tablename__ = "telegram_connect_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    code = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    expires_at = Column(DateTime, index=True, nullable=False)
    is_used = Column(Boolean, default=False, index=True)

    user = relationship("User")



