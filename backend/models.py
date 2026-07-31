from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, CheckConstraint
from sqlalchemy.orm import relationship
import datetime
from backend.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True)
    title = Column(String)
    platform = Column(String) # 'amazon' or 'flipkart'
    product_id = Column(String, index=True) # ID from the platform
    status = Column(String, default="PENDING")
    
    image_url = Column(String, nullable=True)
    brand = Column(String, nullable=True, index=True)
    category = Column(String, nullable=True, index=True)
    
    retry_count = Column(Integer, default=0)
    last_failure = Column(DateTime, nullable=True)
    last_failure_reason = Column(String, nullable=True)
    
    price_snapshots = relationship("PriceSnapshot", back_populates="product", cascade="all, delete-orphan")
    alert_thresholds = relationship("AlertThreshold", back_populates="product")

class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    price = Column(Float)
    mrp_shown = Column(Float)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    is_fake_discount = Column(Boolean, default=False)
    
    __table_args__ = (
        CheckConstraint('price > 0', name='check_price_positive'),
        CheckConstraint('mrp_shown > 0', name='check_mrp_positive'),
    )

    product = relationship("Product", back_populates="price_snapshots")

class AlertThreshold(Base):
    __tablename__ = "alert_thresholds"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    phone_number = Column(String) # For WhatsApp
    threshold_price = Column(Float)
    status = Column(String, default="ACTIVE") # ACTIVE, TRIGGERED, FAILED

    product = relationship("Product", back_populates="alert_thresholds")
