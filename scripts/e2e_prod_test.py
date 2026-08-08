import requests
import time
import os

BASE_URL = "https://smart-price-tracker-xdgm.onrender.com"

def test_prod_e2e():
    print("=== Phase 5.0.14: Step 7 — Production Celery E2E Verification ===")
    
    # 1. Register User
    email = f"prod_e2e_{os.urandom(4).hex()}@example.com"
    password = "ProdPassword123!"
    print(f"Registering user: {email}")
    reg_res = requests.post(f"{BASE_URL}/auth/register", json={"email": email, "password": password, "name": "Prod E2E User"})
    print(f"POST /auth/register -> {reg_res.status_code}")
    assert reg_res.status_code == 200, f"Register failed: {reg_res.text}"
    
    # 2. Login User
    print("Logging in...")
    login_res = requests.post(f"{BASE_URL}/auth/login", data={"username": email, "password": password})
    print(f"POST /auth/login -> {login_res.status_code}")
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Submit Product Tracking Job (API -> Redis -> Celery)
    test_asin = os.urandom(4).hex().upper()
    amazon_url = f"https://www.amazon.in/dp/{test_asin}1"
    print(f"Tracking product: {amazon_url}")
    track_res = requests.post(f"{BASE_URL}/products/track", json={"url": amazon_url}, headers=headers)
    print(f"POST /products/track -> {track_res.status_code}: {track_res.json()}")
    assert track_res.status_code == 200, f"Track failed: {track_res.text}"
    prod_data = track_res.json()
    prod_id = prod_data["id"]
    initial_status = prod_data["status"]
    print(f"Product ID: {prod_id}, Initial Status in DB: {initial_status}")
    assert initial_status == "PENDING"
    
    # 4. Poll for Celery Worker Execution & DB Status Transition
    print("Polling product status to verify Celery worker execution...")
    start_time = time.time()
    final_status = initial_status
    while time.time() - start_time < 35:
        time.sleep(3)
        get_res = requests.get(f"{BASE_URL}/products/{prod_id}", headers=headers)
        if get_res.status_code == 200:
            current_status = get_res.json()["product"]["status"]
            print(f"[{int(time.time() - start_time)}s] Product Status: {current_status}")
            final_status = current_status
            if current_status in ["SUCCESS", "FAILED"]:
                break
                
    print(f"Terminal Product Status in PostgreSQL: '{final_status}'")
    assert final_status in ["SUCCESS", "FAILED"], f"Celery task did not transition product from PENDING to terminal state (stuck at {final_status})"
    print("✅ E2E Task flow PASSED: API -> Upstash Redis -> Celery Worker -> PostgreSQL update!")

if __name__ == "__main__":
    test_prod_e2e()
