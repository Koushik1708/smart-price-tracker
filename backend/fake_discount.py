from backend.models import PriceSnapshot
from sqlalchemy.orm import Session
import datetime

def detect_fake_discount(db: Session, product_id: int) -> bool:
    """
    Detects if the most recent mrp_shown is a 'fake discount'.
    A fake discount is flagged if the current MRP is significantly higher 
    (e.g. > 10%) than the historical average MRP of the last 30 days.
    """
    thirty_days_ago = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=30)
    
    snapshots = db.query(PriceSnapshot).filter(
        PriceSnapshot.product_id == product_id,
        PriceSnapshot.timestamp >= thirty_days_ago
    ).order_by(PriceSnapshot.timestamp.desc()).all()
    
    if not snapshots or len(snapshots) < 5:
        return False
        
    latest_snapshot = snapshots[0]
    historical_snapshots = snapshots[1:]
    
    avg_mrp = sum(s.mrp_shown for s in historical_snapshots) / len(historical_snapshots)
    
    if latest_snapshot.mrp_shown > avg_mrp * 1.10:
        return True
        
    return False

def update_fake_discount_status(db: Session, snapshot_id: int):
    snapshot = db.query(PriceSnapshot).filter(PriceSnapshot.id == snapshot_id).first()
    if snapshot:
        is_fake = detect_fake_discount(db, snapshot.product_id)
        snapshot.is_fake_discount = is_fake
        db.commit()
        return is_fake
    return False
