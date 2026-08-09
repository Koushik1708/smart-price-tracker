from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.database import get_db
from backend.auth import get_current_user
from backend.models import User, Product, PriceSnapshot, AlertThreshold
from typing import List, Dict, Any
import datetime

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/summary")
def get_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total_tracked = db.query(Product).filter(Product.user_id == current_user.id).count()
    active_alerts = db.query(AlertThreshold).filter(AlertThreshold.user_id == current_user.id, AlertThreshold.status == "ACTIVE").count()
    triggered_alerts = db.query(AlertThreshold).filter(AlertThreshold.user_id == current_user.id, AlertThreshold.status == "TRIGGERED").count()
    failed_products = db.query(Product).filter(Product.user_id == current_user.id, Product.status == "FAILED").count()
    
    today = datetime.datetime.now(datetime.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    products_checked_snapshots = db.query(PriceSnapshot.product_id).join(Product).filter(
        Product.user_id == current_user.id,
        PriceSnapshot.timestamp >= today
    ).distinct().count()
    
    # We don't have a specific check time for failed other than last_failure
    products_failed_today = db.query(Product.id).filter(
        Product.user_id == current_user.id,
        Product.status == "FAILED",
        Product.last_failure >= today
    ).distinct().count()
    
    products_checked_today = products_checked_snapshots + products_failed_today
    
    last_scrape = db.query(PriceSnapshot.timestamp).join(Product).filter(
        Product.user_id == current_user.id
    ).order_by(PriceSnapshot.timestamp.desc()).first()
    
    return {
        "total_tracked_products": total_tracked,
        "active_alerts": active_alerts,
        "triggered_alerts": triggered_alerts,
        "failed_products": failed_products,
        "products_checked_today": products_checked_today,
        "last_scrape_time": last_scrape[0] if last_scrape else None
    }

@router.get("/activity")
def get_activity(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    activities = []
    
    # 1. Recent Price Snapshots
    snapshots_query = """
    WITH Ranked AS (
        SELECT 
            s.id, s.product_id, s.price, s.timestamp,
            LAG(s.price) OVER (PARTITION BY s.product_id ORDER BY s.timestamp ASC) as prev_price,
            p.title, p.image_url
        FROM price_snapshots s
        JOIN products p ON s.product_id = p.id
        WHERE p.user_id = :user_id
    )
    SELECT * FROM Ranked 
    ORDER BY timestamp DESC LIMIT 20
    """
    snapshots = db.execute(text(snapshots_query), {"user_id": current_user.id}).fetchall()
    
    for row in snapshots:
        event_type = "PRICE_UPDATED"
        if row.prev_price is not None:
            if row.price < row.prev_price:
                event_type = "PRICE_DROPPED"
            elif row.price > row.prev_price:
                event_type = "PRICE_INCREASED"
        
        activities.append({
            "type": event_type,
            "product_title": row.title,
            "image_url": row.image_url,
            "current_price": row.price,
            "previous_price": row.prev_price,
            "timestamp": row.timestamp
        })
        
    # 2. Recent Failures
    failures = db.query(Product).filter(
        Product.user_id == current_user.id,
        Product.last_failure != None
    ).order_by(Product.last_failure.desc()).limit(10).all()
    
    for p in failures:
        activities.append({
            "type": "SCRAPE_FAILED",
            "product_title": p.title,
            "image_url": p.image_url,
            "reason": p.last_failure_reason,
            "timestamp": p.last_failure
        })
        
    # We sort by timestamp descending and take top 20
    # Handle both string and datetime parsing correctly
    def parse_time(t):
        if isinstance(t, str):
            # SQLite returns string for datetime
            try:
                # Truncate fractional seconds for parsing if needed or use fromisoformat
                dt = datetime.datetime.fromisoformat(t.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=datetime.timezone.utc)
                return dt
            except Exception:
                return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
        elif isinstance(t, datetime.datetime):
            if t.tzinfo is None:
                return t.replace(tzinfo=datetime.timezone.utc)
            return t
        return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
        
    activities.sort(key=lambda x: parse_time(x["timestamp"]), reverse=True)
    
    return activities[:20]

@router.get("/price-drops")
def get_price_drops(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = """
    WITH RankedSnapshots AS (
        SELECT 
            s.product_id,
            s.price,
            s.timestamp,
            LAG(s.price) OVER (PARTITION BY s.product_id ORDER BY s.timestamp ASC) as prev_price,
            ROW_NUMBER() OVER (PARTITION BY s.product_id ORDER BY s.timestamp DESC) as rn
        FROM price_snapshots s
        JOIN products p ON s.product_id = p.id
        WHERE p.user_id = :user_id
    )
    SELECT 
        p.image_url as image, 
        p.title as title, 
        r.prev_price as previous_price, 
        r.price as current_price, 
        (r.prev_price - r.price) as savings, 
        ROUND(CAST(((r.prev_price - r.price) / r.prev_price * 100) AS NUMERIC), 2) as savings_percent, 
        r.timestamp
    FROM RankedSnapshots r
    JOIN products p ON r.product_id = p.id
    WHERE r.rn = 1 AND r.prev_price IS NOT NULL AND r.price < r.prev_price
    ORDER BY savings DESC
    LIMIT 5;
    """
    
    results = db.execute(text(query), {"user_id": current_user.id}).fetchall()
    
    return [dict(r._mapping) for r in results]

@router.get("/recent-products")
def get_recent_products(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Recently checked products -> Order by last_failure or last price snapshot
    # Since we can't easily coalesce a child table in a fast ORM query without joining,
    # let's write a SQL query to get the greatest of last_failure and max snapshot timestamp
    query = """
    WITH RankedSnapshots AS (
        SELECT 
            product_id,
            price,
            timestamp as last_snap_time,
            ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY timestamp DESC) as rn
        FROM price_snapshots
    ),
    LastSnap AS (
        SELECT product_id, price, last_snap_time
        FROM RankedSnapshots
        WHERE rn = 1
    )
    SELECT 
        p.id, p.image_url as image, p.title, 
        COALESCE(ls.price, 0) as current_price,
        p.status,
        CASE 
            WHEN ls.last_snap_time IS NOT NULL AND p.last_failure IS NOT NULL THEN
                CASE WHEN ls.last_snap_time >= p.last_failure THEN ls.last_snap_time ELSE p.last_failure END
            ELSE COALESCE(ls.last_snap_time, p.last_failure)
        END as last_checked
    FROM products p
    LEFT JOIN LastSnap ls ON p.id = ls.product_id
    WHERE p.user_id = :user_id
    ORDER BY last_checked DESC NULLS LAST
    LIMIT 10;
    """
    
    results = db.execute(text(query), {"user_id": current_user.id}).fetchall()
    
    return [dict(r._mapping) for r in results]
