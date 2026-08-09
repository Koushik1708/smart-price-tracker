import pytest
import datetime
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import Base, engine, get_db
from backend.models import User, Product, PriceSnapshot
from backend.auth import create_access_token, get_password_hash
from sqlalchemy.orm import sessionmaker

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def test_setup():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Clean up any previous test user
    existing_user = db.query(User).filter(User.email == "dashboardtest@example.com").first()
    if existing_user:
        db.delete(existing_user)
        db.commit()

    # Create test user
    user = User(email="dashboardtest@example.com", password_hash=get_password_hash("Password123!"), name="Dashboard Tester")
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create products
    p1 = Product(user_id=user.id, title="Test Phone", url="http://amazon.in/dp/TEST1", image_url="http://img1.jpg", status="HEALTHY")
    p2 = Product(user_id=user.id, title="Test Laptop", url="http://amazon.in/dp/TEST2", image_url="http://img2.jpg", status="FAILED", last_failure=datetime.datetime.now(datetime.timezone.utc), last_failure_reason="404")
    db.add_all([p1, p2])
    db.commit()
    db.refresh(p1)
    db.refresh(p2)

    # Create price snapshots for p1 (price dropped from 50000 to 45000)
    now = datetime.datetime.now(datetime.timezone.utc)
    s1 = PriceSnapshot(product_id=p1.id, price=50000.0, mrp_shown=60000.0, timestamp=now - datetime.timedelta(days=2))
    s2 = PriceSnapshot(product_id=p1.id, price=45000.0, mrp_shown=60000.0, timestamp=now - datetime.timedelta(days=1))
    db.add_all([s1, s2])
    db.commit()

    token = create_access_token({"sub": user.email})
    
    yield {"db": db, "token": token, "user": user, "p1": p1, "p2": p2}
    
    db.close()

def test_price_drops_endpoint(test_setup):
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {test_setup['token']}"}
    response = client.get("/dashboard/price-drops", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["title"] == "Test Phone"
    assert data[0]["previous_price"] == 50000.0
    assert data[0]["current_price"] == 45000.0
    assert data[0]["savings"] == 5000.0
    assert data[0]["savings_percent"] == 10.0

def test_recent_products_endpoint(test_setup):
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {test_setup['token']}"}
    response = client.get("/dashboard/recent-products", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    titles = [p["title"] for p in data]
    assert "Test Phone" in titles
    assert "Test Laptop" in titles
