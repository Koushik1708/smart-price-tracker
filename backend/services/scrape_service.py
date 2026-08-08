import logging
from scraper.runner import scrape_single_product
from backend.tracing import get_traced_logger, start_span, end_span, ctx_span_id, ctx_parent_span_id, ctx_span_name

logger = get_traced_logger(__name__)

def scrape_product(product_id: int):
    """
    Wrapper around the Playwright scraper to isolate it from the worker and API layers.
    """
    prev_span = ctx_span_id.get()
    prev_parent = ctx_parent_span_id.get()
    prev_name = ctx_span_name.get()
    
    scraper_span_id = start_span("Scraper")
    
    logger.info(f"Scraper execution started for product {product_id}", extra={"event": "scrape_started"})
    
    try:
        # We delegate to the actual isolated scraper function
        scrape_single_product(product_id)
    except Exception as e:
        logger.error(f"Error in scrape_service for product_id {product_id}: {e}")
        raise
    finally:
        logger.info(f"Scraper execution finished for product {product_id}", extra={"event": "scrape_finished"})
        end_span(previous_span_id=prev_span, previous_parent_id=prev_parent, previous_span_name=prev_name)
