import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models import PriceSnapshot

def run_cleanup():
    db = SessionLocal()
    invalid_rows = db.query(PriceSnapshot).filter(
        (PriceSnapshot.price <= 0) | (PriceSnapshot.mrp_shown <= 0)
    ).all()
    
    count = len(invalid_rows)
    print(f"Found {count} invalid PriceSnapshot rows.")
    
    if count > 0:
        for row in invalid_rows:
            db.delete(row)
        db.commit()
        print(f"Deleted {count} invalid rows.")
    else:
        print("No cleanup needed.")
        
    db.close()

if __name__ == "__main__":
    run_cleanup()
