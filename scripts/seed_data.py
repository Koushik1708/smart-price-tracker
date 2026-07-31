import sys
import os
import random
import datetime

# Add parent directory to path so we can import backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine, Base, SessionLocal
from backend.models import Product, PriceSnapshot

# Sample tech products
PRODUCTS = [
    {"title": "iPhone 15 (128 GB)", "base_price": 72999, "platform": "amazon", "url_base": "https://www.amazon.in/dp/B0CHX1W1XY"},
    {"title": "Samsung Galaxy S24 Ultra", "base_price": 129999, "platform": "amazon", "url_base": "https://www.amazon.in/dp/B0CS9Y3PXP"},
    {"title": "Sony WH-1000XM5", "base_price": 29990, "platform": "flipkart", "url_base": "https://www.flipkart.com/sony-wh-1000xm5/p/itm123"},
    {"title": "MacBook Air M2", "base_price": 99900, "platform": "amazon", "url_base": "https://www.amazon.in/dp/B0B3C91WJW"},
    {"title": "Nothing Phone (2)", "base_price": 39999, "platform": "flipkart", "url_base": "https://www.flipkart.com/nothing-phone-2/p/itm456"},
]

def seed_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(Product).first():
        print("Database already seeded.")
        return

    print("Seeding ~100 products...")
    
    products_inserted = []
    
    for i in range(1, 101):
        base = PRODUCTS[i % len(PRODUCTS)]
        product_id = f"{base['platform'][:3]}-{1000+i}"
        
        prod = Product(
            url=f"{base['url_base']}?var={i}",
            platform=base['platform'],
            product_id=product_id,
            title=f"{base['title']} - Variant {i}"
        )
        db.add(prod)
        db.commit()
        db.refresh(prod)
        products_inserted.append((prod, base))

    print("Seeding price history...")
    
    now = datetime.datetime.utcnow()
    for prod, base in products_inserted:
        current_mrp = base['base_price'] * 1.2 # MRP is 20% higher
        
        for days_ago in range(30, -1, -1):
            date = now - datetime.timedelta(days=days_ago)
            
            mrp_shown = current_mrp
            # 20% of products get a fake discount (MRP hike) in the last 3 days
            if days_ago <= 3 and prod.id % 5 == 0: 
                mrp_shown = current_mrp * 1.3
            
            price = base['base_price'] * random.uniform(0.9, 1.1)
            if days_ago == 0 and prod.id % 5 == 0:
                price = base['base_price'] * 0.8 # Sale price today
                
            snapshot = PriceSnapshot(
                product_id=prod.id,
                price=round(price, 2),
                mrp_shown=round(mrp_shown, 2),
                timestamp=date,
                is_fake_discount=False 
            )
            db.add(snapshot)
    
    db.commit()
    db.close()
    print("Seeding complete.")

if __name__ == "__main__":
    seed_db()
