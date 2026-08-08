import sys
import os
import asyncio
import datetime
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models import Product, PriceSnapshot
from scraper.base import PriceExtractionError
from scraper.amazon_scraper import AmazonScraper
from scraper.flipkart_scraper import FlipkartScraper
import logging
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file so Twilio gets real credentials
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "60"))

# Structured Logging Setup (matches main.py)
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if hasattr(record, "product_id"):
            log_obj["product_id"] = record.product_id
        if hasattr(record, "platform"):
            log_obj["platform"] = record.platform
        if hasattr(record, "url"):
            log_obj["url"] = record.url
        if hasattr(record, "status"):
            log_obj["status"] = record.status
        if hasattr(record, "processing_time"):
            log_obj["processing_time"] = record.processing_time
        if hasattr(record, "error_reason"):
            log_obj["error_reason"] = record.error_reason

        return json.dumps(log_obj)

log_handler = logging.StreamHandler(sys.stdout)
log_handler.setFormatter(JSONFormatter())
logging.basicConfig(level=logging.INFO, handlers=[log_handler])
logger = logging.getLogger(__name__)

async def _async_scrape_single_product(product_id: int):
    # Need its own session because it runs in the background
    db = SessionLocal()
    start_time = time.time()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return
            
        if product.status == "FAILED" and product.retry_count >= 3:
            logger.warning(f"Product {product.url} exceeded max retries. Skipping.", extra={"product_id": product.id, "url": product.url})
            return


        product.status = "SCRAPING"
        db.commit()

        logger.info(f"Scraping {product.url}", extra={"product_id": product.id, "url": product.url, "platform": product.platform})
        
        amazon_scraper = AmazonScraper()
        flipkart_scraper = FlipkartScraper()
        
        scraper = amazon_scraper if product.platform == 'amazon' else flipkart_scraper
        
        data = await scraper.fetch_product_data(product.url)
        if data:
            if data.get('current_price', 0) <= 0.0 or data.get('mrp_shown', 0) <= 0.0:
                reason = "Extracted price or mrp was zero or less."
                logger.error(f"Failed to extract valid price/mrp for {product.url}.", extra={"product_id": product.id, "url": product.url, "error_reason": reason})
                product.status = "FAILED"
                product.retry_count += 1
                product.last_failure = datetime.datetime.utcnow()
                product.last_failure_reason = reason
            else:
                logger.info(f"Got data: {data['current_price']} / {data['mrp_shown']}", extra={"product_id": product.id, "url": product.url})
                
                # Check for duplicate snapshot
                from backend.fake_discount import detect_fake_discount
                
                # We need to simulate detect_fake_discount logic for the incoming snapshot
                thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
                historical_snapshots = db.query(PriceSnapshot).filter(
                    PriceSnapshot.product_id == product.id,
                    PriceSnapshot.timestamp >= thirty_days_ago
                ).order_by(PriceSnapshot.timestamp.desc()).all()
                
                is_fake_discount = False
                if historical_snapshots and len(historical_snapshots) >= 4:
                    avg_mrp = sum(s.mrp_shown for s in historical_snapshots) / len(historical_snapshots)
                    if data['mrp_shown'] > avg_mrp * 1.10:
                        is_fake_discount = True

                latest = historical_snapshots[0] if historical_snapshots else db.query(PriceSnapshot).filter(PriceSnapshot.product_id == product.id).order_by(PriceSnapshot.timestamp.desc()).first()
                
                if latest and abs(latest.price - data['current_price']) < 0.01 and abs(latest.mrp_shown - data['mrp_shown']) < 0.01 and latest.is_fake_discount == is_fake_discount:
                    logger.info("No price change detected. Skipping insertion.", extra={"product_id": product.id, "url": product.url})
                    snapshot_inserted = False
                else:
                    snapshot = PriceSnapshot(
                        product_id=product.id,
                        price=data['current_price'],
                        mrp_shown=data['mrp_shown'],
                        timestamp=datetime.datetime.utcnow(),
                        is_fake_discount=is_fake_discount
                    )
                    db.add(snapshot)
                    snapshot_inserted = True
                
                if product.title == "Tracking Pending..." and data.get('title'):
                    product.title = data['title']
                if product.product_id == "unknown" and data.get('product_id'):
                    product.product_id = data['product_id']
                    
                if (not product.image_url or product.image_url.strip() == "") and data.get('image_url'):
                    product.image_url = data['image_url']
                if (not product.brand or product.brand.strip() == "") and data.get('brand'):
                    product.brand = data['brand']
                if (not product.category or product.category.strip() == "") and data.get('category'):
                    product.category = data['category']
                    
                product.status = "SUCCESS"
                product.retry_count = 0
                product.last_failure = None
                product.last_failure_reason = None
                
                # Check for active alerts regardless of snapshot insertion
                from backend.models import AlertThreshold
                from backend.notifications import TwilioSandboxProvider
                
                active_alerts = db.query(AlertThreshold).filter(
                    AlertThreshold.product_id == product.id,
                    AlertThreshold.status == "ACTIVE"
                ).all()
                
                if active_alerts:
                    notifier = TwilioSandboxProvider()
                    for alert in active_alerts:
                        if data['current_price'] <= alert.threshold_price:
                            msg = f"PRICE DROP ALERT!\n\n{product.title}\n\nCurrent Price: ₹{data['current_price']}\nTarget: ₹{alert.threshold_price}\n\nLink: {product.url}"
                            success = notifier.send_alert(alert.phone_number, msg)
                            if success:
                                alert.status = "TRIGGERED"
                                db.add(alert)
                            else:
                                logger.warning(f"Failed to send alert {alert.id} to {alert.phone_number}.", extra={"product_id": product.id})
        else:
            reason = "Scraper returned no data."
            logger.error(f"Failed to scrape {product.url}", extra={"product_id": product.id, "url": product.url, "error_reason": reason})
            product.status = "FAILED"
            product.retry_count += 1
            product.last_failure = datetime.datetime.utcnow()
            product.last_failure_reason = reason
    except PriceExtractionError as e:
        reason = str(e)
        logger.error(f"Price extraction failed for {product.url}: {e}.", extra={"product_id": product.id, "url": product.url, "error_reason": reason})
        product.status = "FAILED"
        product.retry_count += 1
        product.last_failure = datetime.datetime.utcnow()
        product.last_failure_reason = reason
    except Exception as e:
        reason = str(e)
        logger.error(f"Unexpected error scraping {product.url}: {e}", extra={"product_id": product.id, "url": product.url, "error_reason": reason})
        product.status = "FAILED"
        product.retry_count += 1
        product.last_failure = datetime.datetime.utcnow()
        product.last_failure_reason = reason
    finally:
        db.commit()
        db.close()
        process_time = time.time() - start_time
        logger.info(f"Finished scraping {product_id}", extra={"product_id": product_id, "processing_time": f"{process_time:.4f}s"})

def scrape_single_product(product_id: int):
    # Run the async logic in a fresh event loop so Playwright subprocesses work on Windows
    asyncio.run(_async_scrape_single_product(product_id))

async def run_scraper():
    db = SessionLocal()
    products = db.query(Product).all()
    db.close()
    
    for product in products:
        if product.status == "FAILED" and product.retry_count >= 3:
            continue
        await scrape_single_product(product.id)
        await asyncio.sleep(2) # Randomized delay should be used in prod
        
    logger.info("Scraping run complete.")

if __name__ == "__main__":
    asyncio.run(run_scraper())
