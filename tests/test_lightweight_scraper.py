import pytest
from unittest.mock import MagicMock, patch
from scraper.amazon_scraper import AmazonScraper
from scraper.base import PriceExtractionError
from backend.database import Base, engine, SessionLocal
from backend.models import User, Product

def test_amazon_fast_http_fetch_success():
    scraper = AmazonScraper()
    html_content = """
    <html>
        <body>
            <span id="productTitle">   Test Amazon Product Title   </span>
            <span class="a-price-whole">1,299.</span>
            <span class="a-text-price"><span class="a-offscreen">₹1,999</span></span>
            <img id="landingImage" src="https://m.media-amazon.com/images/I/test.jpg" />
            <a id="bylineInfo">Visit the Test Store</a>
            <div id="wayfinding-breadcrumbs_container">Electronics &gt; Audio</div>
        </body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html_content

    with patch("requests.get", return_value=mock_resp):
        res = scraper._fast_http_fetch("https://www.amazon.in/dp/B0TESTASIN")
        assert res is not None
        assert res["title"] == "Test Amazon Product Title"
        assert res["current_price"] == 1299.0
        assert res["mrp_shown"] == 1999.0
        assert res["product_id"] == "B0TESTASIN"
        assert res["platform"] == "amazon"
        assert res["image_url"] == "https://m.media-amazon.com/images/I/test.jpg"

def test_amazon_fast_http_fetch_failure_returns_none():
    scraper = AmazonScraper()
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.text = "Not Found"

    with patch("requests.get", return_value=mock_resp):
        res = scraper._fast_http_fetch("https://www.amazon.in/dp/B0TESTASIN")
        assert res is None

def test_stale_product_reconciliation():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Create test user
    user = User(email="reconcile_test@example.com", password_hash="pw")
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create product in SCRAPING state
    p = Product(
        user_id=user.id,
        url="https://www.amazon.in/dp/B0STALEPROD",
        platform="amazon",
        status="SCRAPING",
        title="Tracking Pending..."
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    # Run reconciliation
    from backend.main import reconcile_stale_products
    reconcile_stale_products()

    db.refresh(p)
    assert p.status == "FAILED"
    assert "interrupted by worker process" in p.last_failure_reason
    
    # Cleanup
    db.delete(p)
    db.delete(user)
    db.commit()
    db.close()
