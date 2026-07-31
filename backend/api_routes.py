from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.database import get_db
from backend.models import Product, PriceSnapshot, AlertThreshold
from backend.notifications import TwilioSandboxProvider
from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import List
import os

router = APIRouter()

class ProductCreate(BaseModel):
    url: HttpUrl = Field(..., description="The Amazon India or Flipkart product URL")

    @field_validator("url")
    def validate_url_domain(cls, v):
        url_str = str(v)
        if "amazon.in" not in url_str and "amzn.in" not in url_str and "flipkart.com" not in url_str:
            raise ValueError("Only Amazon India and Flipkart URLs are supported.")
        return v

from typing import Optional

class ProductResponse(BaseModel):
    id: int
    url: str
    title: str
    platform: str
    product_id: str
    status: str = "PENDING"
    image_url: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    
    class Config:
        from_attributes = True
        orm_mode = True

import requests
import re
from urllib.parse import urlparse, parse_qs

def canonicalize_url(url: str) -> dict:
    url_str = str(url)
    if "amazon.in" not in url_str and "amzn.in" not in url_str and "flipkart.com" not in url_str:
        raise ValueError("Only Amazon India and Flipkart URLs are supported.")
        
    try:
        response = requests.head(url_str, allow_redirects=True, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        resolved_url = response.url
    except requests.RequestException:
        resolved_url = url_str
        
    parsed = urlparse(resolved_url)
    
    if "amazon.in" in resolved_url or "amzn.in" in resolved_url:
        platform = "amazon"
        match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", resolved_url)
        if match:
            pid = match.group(1)
            canonical_url = f"https://www.amazon.in/dp/{pid}"
        else:
            pid = "unknown"
            canonical_url = resolved_url
            
    elif "flipkart.com" in resolved_url:
        platform = "flipkart"
        match = re.search(r"/p/(itm[a-zA-Z0-9]+)", resolved_url)
        if match:
            itm_id = match.group(1)
            qs = parse_qs(parsed.query)
            pid = qs.get("pid", [itm_id])[0] 
            # Preserve the SEO path to ensure Flipkart returns SSR JSON-LD
            canonical_url = f"https://www.flipkart.com{parsed.path}?pid={pid}"
        else:
            pid = "unknown"
            canonical_url = resolved_url
    else:
        raise ValueError("Unsupported platform")
        
    return {
        "platform": platform,
        "pid": pid,
        "canonical_url": canonical_url
    }

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/health")
def get_health(db: Session = Depends(get_db)):
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "playwright": "unknown",
        "twilio": "unknown",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "environment": os.getenv("ENVIRONMENT", "development")
    }

    # Check Database
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "ok"
    except Exception as e:
        health_status["database"] = "error"
        health_status["status"] = "unhealthy"

    # Check Playwright
    try:
        import playwright
        health_status["playwright"] = "ok"
    except ImportError:
        health_status["playwright"] = "error"
        health_status["status"] = "unhealthy"

    # Check Notifications
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    num = os.getenv("TWILIO_WHATSAPP_NUMBER")
    
    if sid and token and num:
        health_status["twilio"] = "configured"
    else:
        health_status["twilio"] = "not_configured"
        
    return health_status

@router.get("/version")
def get_version():
    import datetime
    return {
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "build_date": datetime.date.today().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "git_commit": os.getenv("VERCEL_GIT_COMMIT_SHA", "unknown")
    }

@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    total_products = db.query(Product).count()
    successful_scrapes = db.query(Product).filter(Product.status == "SUCCESS").count()
    failed_scrapes = db.query(Product).filter(Product.status == "FAILED").count()
    pending_products = db.query(Product).filter(Product.status == "PENDING").count()
    active_alerts = db.query(AlertThreshold).filter(AlertThreshold.status == "ACTIVE").count()
    fake_discounts_detected = db.query(PriceSnapshot).filter(PriceSnapshot.is_fake_discount == True).count()
    
    return {
        "total_products": total_products,
        "successful_scrapes": successful_scrapes,
        "failed_scrapes": failed_scrapes,
        "pending_products": pending_products,
        "active_alerts": active_alerts,
        "fake_discounts_detected": fake_discounts_detected
    }

@router.post("/products/track", response_model=ProductResponse)
@limiter.limit("10/minute")
def track_product(request: Request, product: ProductCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        canonical_data = canonicalize_url(str(product.url))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    db_product = db.query(Product).filter(Product.url == canonical_data["canonical_url"]).first()
    if db_product:
        return db_product
        
    new_product = Product(
        url=canonical_data["canonical_url"],
        platform=canonical_data["platform"],
        product_id=canonical_data["pid"],
        title="Tracking Pending...",
        status="PENDING",
        retry_count=0
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    
    from scraper.runner import scrape_single_product
    background_tasks.add_task(scrape_single_product, new_product.id)
    
    return new_product

@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}

@router.post("/products/{product_id}/retry")
@limiter.limit("5/minute")
def retry_failed_product(request: Request, product_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    if product.status != "FAILED":
        raise HTTPException(status_code=400, detail="Only failed products can be retried")
        
    product.status = "PENDING"
    product.retry_count = 0  # Reset retry count on manual retry
    db.commit()
    
    from scraper.runner import scrape_single_product
    background_tasks.add_task(scrape_single_product, product.id)
    
    return {"message": "Product retry initiated", "status": "PENDING"}

@router.get("/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    snapshots = db.query(PriceSnapshot).filter(PriceSnapshot.product_id == product_id).order_by(PriceSnapshot.timestamp.asc()).all()
    
    is_fake_discount = False
    if snapshots and snapshots[-1].is_fake_discount:
        is_fake_discount = True
        
    from backend.analytics import calculate_statistics, analyze_trend, calculate_deal_score
    statistics = calculate_statistics(snapshots)
    trend = analyze_trend(snapshots)
    deal_score = calculate_deal_score(product, snapshots, is_fake_discount)
        
    return {
        "product": product,
        "history": snapshots,
        "is_fake_discount": is_fake_discount,
        "statistics": statistics,
        "trend": trend,
        "deal_score": deal_score
    }

from fastapi.responses import StreamingResponse
import io
import csv

@router.get("/products/{product_id}/export")
def export_product_csv(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    snapshots = db.query(PriceSnapshot).filter(PriceSnapshot.product_id == product_id).order_by(PriceSnapshot.timestamp.asc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Metadata
    writer.writerow(["Product Name", product.title])
    writer.writerow(["Platform", product.platform.capitalize()])
    writer.writerow(["Product URL", product.url])
    writer.writerow([]) # Blank line
    
    # Headers
    writer.writerow(["Timestamp", "Price", "MRP", "Fake Discount"])
    
    # Data
    for snap in snapshots:
        writer.writerow([
            snap.timestamp.isoformat(),
            snap.price,
            snap.mrp_shown,
            "Yes" if snap.is_fake_discount else "No"
        ])
        
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=product_{product_id}_history.csv"}
    )

from math import ceil

@router.get("/products/search/")
def search_products(
    q: str = "", 
    platform: str = "", 
    category: str = "", 
    page: int = 1, 
    page_size: int = 50, 
    db: Session = Depends(get_db)
):
    query = db.query(Product)
    
    if q:
        query = query.filter(
            (Product.title.ilike(f"%{q}%")) | (Product.brand.ilike(f"%{q}%"))
        )
    if platform:
        query = query.filter(Product.platform == platform)
    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
        
    total_products = query.count()
    total_pages = ceil(total_products / page_size) if total_products > 0 else 1
    
    page = max(1, min(page, total_pages))
    skip = (page - 1) * page_size
    
    products = query.order_by(Product.id.desc()).offset(skip).limit(page_size).all()
    
    return {
        "products": products,
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_products": total_products,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
    }

class AlertCreate(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=15, pattern=r"^\+?\d+$")
    threshold_price: float = Field(..., gt=0)

@router.post("/products/{product_id}/alerts")
@limiter.limit("5/minute")
def create_alert(request: Request, product_id: int, alert: AlertCreate, db: Session = Depends(get_db)):
    phone_number = alert.phone_number.strip()
    if phone_number.startswith("+"):
        phone_number = f"whatsapp:{phone_number}"
        
    if not phone_number.startswith("whatsapp:+") or len(phone_number) < 12:
        raise HTTPException(status_code=400, detail="Phone number must start with '+' (e.g. +91...) and include country code")
        
    alert.phone_number = phone_number
        
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    new_alert = AlertThreshold(
        product_id=product.id,
        phone_number=alert.phone_number,
        threshold_price=alert.threshold_price,
        status="ACTIVE"
    )
    
    notifier = TwilioSandboxProvider()
    msg = f"✅ Price Alert Activated!\n\nProduct: {product.title}\n\nWe will notify you here when the price drops to ₹{alert.threshold_price} or below."
    
    success = notifier.send_alert(alert.phone_number, msg)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to send confirmation WhatsApp message. Please ensure your number has joined the Twilio Sandbox.")
        
    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)
    return new_alert

@router.get("/products/{product_id}/alerts")
def get_alerts(product_id: int, db: Session = Depends(get_db)):
    alerts = db.query(AlertThreshold).filter(AlertThreshold.product_id == product_id).all()
    return alerts
