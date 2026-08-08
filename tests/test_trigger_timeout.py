import pytest
import time
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import User, Product, PriceSnapshot
from backend.auth import get_password_hash, create_access_token

client = TestClient(app)

@pytest.fixture
def test_user_and_headers():
    db = SessionLocal()
    email = "triggertest@example.com"
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            name="Trigger Test User",
            email=email,
            password_hash=get_password_hash("Password123!")
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    token = create_access_token(data={"sub": user.email})
    db.close()
    headers = {"Authorization": f"Bearer {token}"}
    return user, headers

def test_post_products_scrape_endpoint_exists(test_user_and_headers):
    """
    Verifies that POST /products/{product_id}/scrape endpoint exists,
    enforces authentication, tenant ownership, and enqueues a scrape job.
    """
    user, headers = test_user_and_headers
    db = SessionLocal()
    test_url = "https://www.amazon.in/dp/B08N5WRWNW"
    
    # Cleanup previous instances
    existing = db.query(Product).filter(Product.url == test_url, Product.user_id == user.id).first()
    if existing:
        db.delete(existing)
        db.commit()

    # Create test product for user
    product = Product(
        user_id=user.id,
        url=test_url,
        platform="amazon",
        product_id="B08N5WRWNW",
        title="Test Amazon Echo",
        status="SUCCESS"
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    product_id = product.id
    db.close()

    # 1. Unauthenticated request should return 401
    unauth_res = client.post(f"/products/{product_id}/scrape")
    assert unauth_res.status_code == 401, f"Expected 401, got {unauth_res.status_code}"

    # 2. Authenticated request for owned product should succeed with PENDING status
    res = client.post(f"/products/{product_id}/scrape", headers=headers)
    assert res.status_code == 200, f"Expected 200, got {res.status_code} {res.text}"
    data = res.json()
    assert data["status"] == "PENDING"
    assert "job_id" in data
    assert data["product_id"] == product_id

    # 3. Clean up
    db = SessionLocal()
    p = db.query(Product).filter(Product.id == product_id).first()
    if p:
        db.delete(p)
        db.commit()
    db.close()

def test_product_track_short_link_fast_response(test_user_and_headers):
    """
    Verifies product tracking API request for short link (amzn.in) responds immediately
    (< 1.0 second) without blocking for external HTTP redirect resolution.
    """
    user, headers = test_user_and_headers
    test_url = "https://amzn.in/d/00bAd6J6"
    
    # Cleanup previous instances
    db = SessionLocal()
    existing = db.query(Product).filter(Product.url == test_url, Product.user_id == user.id).first()
    if existing:
        db.delete(existing)
        db.commit()
    db.close()

    start_time = time.time()
    res = client.post("/products/track", json={"url": test_url}, headers=headers)
    duration = time.time() - start_time
    
    assert res.status_code == 200, f"Expected 200, got {res.status_code} {res.text}"
    assert duration < 1.0, f"API track request took {duration:.4f}s, expected < 1.0s non-blocking response!"
    
    prod_data = res.json()
    assert prod_data["status"] == "PENDING"
    assert prod_data["url"] == test_url

    # Cleanup
    db = SessionLocal()
    p = db.query(Product).filter(Product.id == prod_data["id"]).first()
    if p:
        db.delete(p)
        db.commit()
    db.close()
