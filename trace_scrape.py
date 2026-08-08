import sys
import logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

from backend.database import SessionLocal
from backend.models import Product
from backend.services.scrape_service import scrape_product

db = SessionLocal()
p = db.query(Product).filter(Product.status == 'PENDING').first()
if not p:
    print('No pending product found')
    sys.exit(0)
    
print(f'Starting scrape for product {p.id}')
try:
    scrape_product(p.id)
except Exception as e:
    print(f'Exception: {e}')
    
p2 = db.query(Product).filter(Product.id == p.id).first()
print(f'Product {p2.id} status is now: {p2.status}')
