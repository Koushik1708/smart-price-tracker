import sys
import os
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, Base, engine
from backend.models import User, Product, AlertThreshold, PriceSnapshot

BASE_URL = os.getenv("BASE_URL", "http://localhost:8001")

def create_user(email, password, name):
    response = requests.post(f"{BASE_URL}/auth/register", json={"email": email, "password": password, "name": name})
    assert response.status_code == 200, f"Register failed: {response.text}"
    return response.json()

def login(email, password):
    response = requests.post(f"{BASE_URL}/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]

def track_product(token, url):
    response = requests.post(f"{BASE_URL}/products/track", json={"url": url}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, f"Track failed: {response.text}"
    return response.json()

def create_alert(token, product_id, phone, threshold):
    response = requests.post(f"{BASE_URL}/products/{product_id}/alerts", json={"phone_number": phone, "threshold_price": threshold}, headers={"Authorization": f"Bearer {token}"})
    return response

def test_isolation():
    print("1. Creating users")
    email_a = f"usera_{os.urandom(4).hex()}@example.com"
    email_b = f"userb_{os.urandom(4).hex()}@example.com"
    
    user_a = create_user(email_a, "passA123", "User A")
    user_b = create_user(email_b, "passB123", "User B")
    
    token_a = login(email_a, "passA123")
    token_b = login(email_b, "passB123")
    
    import time
    print("2. User A Create")
    prod_a1 = track_product(token_a, f"https://www.amazon.in/dp/{os.urandom(4).hex().upper()}1")
    time.sleep(1)
    prod_a2 = track_product(token_a, f"https://www.amazon.in/dp/{os.urandom(4).hex().upper()}2")
    time.sleep(1)
    prod_a3 = track_product(token_a, f"https://www.amazon.in/dp/{os.urandom(4).hex().upper()}3")
    
    print("3. User B Create")
    prod_b1 = track_product(token_b, f"https://www.amazon.in/dp/{os.urandom(4).hex().upper()}1")
    time.sleep(1)
    prod_b2 = track_product(token_b, f"https://www.amazon.in/dp/{os.urandom(4).hex().upper()}2")
    time.sleep(1)
    
    print("4. Verify User A cannot see User B products")
    res = requests.get(f"{BASE_URL}/products/{prod_b1['id']}", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 404, "User A could see User B's product!"
    
    res = requests.get(f"{BASE_URL}/products/search/", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 200
    a_search = res.json()["products"]
    # Should only contain A's products
    for p in a_search:
        assert p["id"] != prod_b1["id"]
        
    print("5. Metrics")
    res_a_metrics = requests.get(f"{BASE_URL}/metrics", headers={"Authorization": f"Bearer {token_a}"})
    res_b_metrics = requests.get(f"{BASE_URL}/metrics", headers={"Authorization": f"Bearer {token_b}"})
    assert res_a_metrics.json()["total_products"] == 3
    assert res_b_metrics.json()["total_products"] == 2
    
    print("6. Alerts isolation")
    res = requests.get(f"{BASE_URL}/products/{prod_b1['id']}/alerts", headers={"Authorization": f"Bearer {token_a}"})
    assert res.json() == [] # Returns empty array or 404, both are isolated.
    
    print("7. CSV export isolation")
    res = requests.get(f"{BASE_URL}/products/{prod_b1['id']}/export", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 404
    
    print("8. Delete isolation")
    res = requests.delete(f"{BASE_URL}/products/{prod_b1['id']}", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 404
    
    print("[SUCCESS] All multi-user isolation checks passed!")

if __name__ == "__main__":
    test_isolation()
