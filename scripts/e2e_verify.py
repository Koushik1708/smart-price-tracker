import os
import sys
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from backend.database import SessionLocal
from backend.models import Product, AlertThreshold, User
from scraper.runner import _async_scrape_single_product, AmazonScraper # type: ignore
import scraper.runner # type: ignore

async def verify():
    db = SessionLocal()
    try:
        # 1. Get default admin user
        admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@letsgo.com")
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            raise Exception("Admin user not found. Please run migrations first.")

        # 2. Get or create a product
        product = db.query(Product).filter(Product.user_id == admin.id).first()
        if not product:
            product = Product(user_id=admin.id, url="https://www.amazon.in/dp/DUMMYID", platform="amazon", product_id="DUMMYID", title="Dummy Product")
            db.add(product)
            db.commit()
            db.refresh(product)

        print(f"Using product: {product.url}")
        
        # 2. Add an alert with a high threshold        # 3. Create an active alert using the user's verified sandbox number
        alert = AlertThreshold(
            user_id=admin.id,
            product_id=product.id,
            threshold_price=9999999.0, # arbitrarily high so it triggers
            phone_number="whatsapp:+919390948443", 
            status="ACTIVE"
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        alert_id = alert.id
        print(f"Created ACTIVE alert ID {alert_id} for threshold 9999999.0")
        
        # 3. Mock the scraper and run
        print("Running scraper...")
        import scraper.amazon_scraper
        from backend.tracing import start_trace, start_span, set_context
        
        # Simulate the middleware and worker contexts since we bypass them here
        start_trace("e2e-request-1234")
        start_span("E2E_Worker")
        set_context(
            job_id="e2e-job-5678",
            job_type="SCRAPE_PRODUCT",
            queue_time_ms=5,
            execution_time_ms=150,
            attempt=1,
            max_attempts=3
        )
        
        class MockAmazonScraper:
            async def fetch_product_data(self, url):
                return {'title': 'Dummy Product', 'current_price': 300.0, 'mrp_shown': 1000.0, 'product_id': 'DUMMYID'}
        
        original_amazon = scraper.runner.AmazonScraper
        scraper.runner.AmazonScraper = MockAmazonScraper  # type: ignore
        
        await _async_scrape_single_product(int(product.id))  # type: ignore
        
        scraper.runner.AmazonScraper = original_amazon
        
        print("Scraper finished.")
        
        # 4. Check alert status
        db.refresh(alert)
        print(f"Alert status is now: {alert.status}")
        assert alert.status == "TRIGGERED", f"Expected TRIGGERED, got {alert.status}"
        print("[OK] End-to-End Verification Passed.")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(verify())
