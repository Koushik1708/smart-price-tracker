import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import Product, PriceSnapshot
from backend.fake_discount import detect_fake_discount

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

def test_no_fake_discount_normal_fluctuation(db):
    product = Product(url="http://test.com/1", platform="amazon", product_id="123")
    db.add(product)
    db.commit()
    
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    for i in range(10):
        snap = PriceSnapshot(
            product_id=product.id, price=900, mrp_shown=1000, 
            timestamp=now - datetime.timedelta(days=i)
        )
        db.add(snap)
    db.commit()
    
    is_fake = detect_fake_discount(db, int(product.id))  # type: ignore
    assert is_fake is False

def test_fake_discount_detected(db):
    product = Product(url="http://test.com/2", platform="amazon", product_id="456")
    db.add(product)
    db.commit()
    
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    
    # Historical MRP was 1000 for 9 days
    for i in range(1, 10):
        snap = PriceSnapshot(
            product_id=product.id, price=900, mrp_shown=1000, 
            timestamp=now - datetime.timedelta(days=i)
        )
        db.add(snap)
        
    # Today, the MRP is bumped to 1500 (50% increase)
    snap = PriceSnapshot(
        product_id=product.id, price=800, mrp_shown=1500, 
        timestamp=now
    )
    db.add(snap)
    db.commit()
    
    is_fake = detect_fake_discount(db, int(product.id))  # type: ignore
    assert is_fake is True

def test_not_enough_history(db):
    product = Product(url="http://test.com/3", platform="amazon", product_id="789")
    db.add(product)
    db.commit()
    
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    for i in range(3):
        snap = PriceSnapshot(
            product_id=product.id, price=900, mrp_shown=1500, 
            timestamp=now - datetime.timedelta(days=i)
        )
        db.add(snap)
    db.commit()
    
    is_fake = detect_fake_discount(db, int(product.id))  # type: ignore
    assert is_fake is False
