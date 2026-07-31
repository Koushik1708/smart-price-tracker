import sys
import os
import datetime
from sqlalchemy.exc import IntegrityError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models import PriceSnapshot, Product

def verify_constraints():
    db = SessionLocal()
    
    # Need a valid product to associate the snapshot with
    product = db.query(Product).first()
    if not product:
        print("No products found in the database. Cannot run verification.")
        db.close()
        return

    print("Attempting to insert a snapshot with price = 0.0...")
    invalid_snapshot = PriceSnapshot(
        product_id=product.id,
        price=0.0,
        mrp_shown=100.0,
        timestamp=datetime.datetime.utcnow()
    )
    
    db.add(invalid_snapshot)
    
    try:
        db.commit()
        print("FAIL: The database accepted an invalid price (0.0). Constraint is missing or not enforced!")
        # Clean up the mistakenly inserted row just in case
        db.delete(invalid_snapshot)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        print("SUCCESS: Database successfully rejected the invalid price (0.0).")
        print(f"Error details: {e._message()}")
        
    print("\nAttempting to insert a snapshot with mrp_shown = 0.0...")
    invalid_snapshot2 = PriceSnapshot(
        product_id=product.id,
        price=100.0,
        mrp_shown=0.0,
        timestamp=datetime.datetime.utcnow()
    )
    
    db.add(invalid_snapshot2)
    try:
        db.commit()
        print("FAIL: The database accepted an invalid mrp (0.0). Constraint is missing or not enforced!")
        db.delete(invalid_snapshot2)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        print("SUCCESS: Database successfully rejected the invalid mrp (0.0).")
        print(f"Error details: {e._message()}")

    db.close()

if __name__ == "__main__":
    verify_constraints()
