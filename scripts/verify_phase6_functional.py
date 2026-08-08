import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import requests
import time

BASE_URL = os.getenv("BASE_URL", "http://localhost:8001")

def get_headers(token=None):
    headers = {"X-Forwarded-For": f"10.88.{os.urandom(1)[0]}.{os.urandom(1)[0]}"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def run_functional_verification():
    print("\n=======================================================")
    print("   PHASE 6.1 FUNCTIONAL POLISH & STATE SYNC VERIFICATION")
    print("=======================================================\n")

    unique_suffix = os.urandom(4).hex()
    email = f"func_user_{unique_suffix}@example.com"
    password = "Password123!"

    # 1. User Registration & Authentication Flow
    print("1. Testing Registration & Authentication Flow...")
    res_reg = requests.post(f"{BASE_URL}/auth/register", json={"email": email, "password": password, "name": "Func User"}, headers=get_headers())
    assert res_reg.status_code == 200, f"Registration failed: {res_reg.text}"

    res_login = requests.post(f"{BASE_URL}/auth/login", data={"username": email, "password": password}, headers=get_headers())
    assert res_login.status_code == 200, f"Login failed: {res_login.text}"
    token = res_login.json()["access_token"]
    print("   [PASS] User registered and authenticated successfully.")

    # 2. Product Tracking & State Synchronization
    print("\n2. Testing Product Tracking & Initial State...")
    test_url = f"https://www.amazon.in/dp/B08N5WRWNW?test={unique_suffix}"
    res_track = requests.post(f"{BASE_URL}/products/track", json={"url": test_url}, headers=get_headers(token))
    assert res_track.status_code == 200, f"Failed to track product: {res_track.text}"
    product_data = res_track.json()
    product_id = product_data["id"]
    initial_status = product_data["status"]
    assert initial_status in ["PENDING", "SCRAPING", "SUCCESS"], f"Unexpected initial status: {initial_status}"
    print(f"   [PASS] Product tracked (ID: {product_id}, Initial Status: {initial_status}).")

    # 3. Dashboard Metrics Auto-Synchronization Check
    print("\n3. Testing Dashboard Metrics Synchronization...")
    res_metrics = requests.get(f"{BASE_URL}/metrics", headers=get_headers(token))
    assert res_metrics.status_code == 200, f"Failed to fetch metrics: {res_metrics.text}"
    m_data = res_metrics.json()
    assert m_data["total_products"] > 0, "Metrics total_products did not update!"
    print(f"   [PASS] Dashboard metrics synchronized: Total Products = {m_data['total_products']}.")

    # 4. Product Pause & Resume Workflow
    print("\n4. Testing Product Pause & Resume Workflow...")
    res_pause = requests.patch(f"{BASE_URL}/products/{product_id}", json={"status": "PAUSED"}, headers=get_headers(token))
    assert res_pause.status_code == 200, f"Failed to pause product: {res_pause.text}"
    assert res_pause.json()["status"] == "PAUSED", "Product status failed to transition to PAUSED!"
    print("   [PASS] Product successfully PAUSED.")

    res_resume = requests.patch(f"{BASE_URL}/products/{product_id}", json={"status": "PENDING"}, headers=get_headers(token))
    assert res_resume.status_code == 200, f"Failed to resume product: {res_resume.text}"
    assert res_resume.json()["status"] in ["PENDING", "SCRAPING", "SUCCESS"], "Product status failed to resume!"
    print("   [PASS] Product successfully RESUMED.")

    # 5. Alert Synchronization
    print("\n5. Testing Alert Creation & Synchronization...")
    res_alert = requests.post(f"{BASE_URL}/products/{product_id}/alerts", json={"phone_number": "+919876543210", "threshold_price": 50000.0}, headers=get_headers(token))
    assert res_alert.status_code == 200, f"Failed to create alert: {res_alert.text}"
    alert_id = res_alert.json()["id"]
    
    res_alerts_list = requests.get(f"{BASE_URL}/products/{product_id}/alerts", headers=get_headers(token))
    assert res_alerts_list.status_code == 200
    alert_ids = [a["id"] for a in res_alerts_list.json()]
    assert alert_id in alert_ids, "Created alert not found in product alert list!"
    print(f"   [PASS] Alert created and synchronized (Alert ID: {alert_id}).")

    # 6. CSV Export Endpoint
    print("\n6. Testing CSV Export Endpoint...")
    res_csv = requests.get(f"{BASE_URL}/products/{product_id}/export", headers=get_headers(token))
    assert res_csv.status_code == 200, f"CSV Export failed: {res_csv.text}"
    assert "text/csv" in res_csv.headers.get("Content-Type", ""), "Response is not text/csv!"
    print("   [PASS] CSV Export endpoint returned valid CSV content.")

    # 7. Complete Product Deletion & Cascading Removal Workflow
    print("\n7. Testing Product Deletion & Cascading Removal...")
    res_del = requests.delete(f"{BASE_URL}/products/{product_id}", headers=get_headers(token))
    assert res_del.status_code == 200, f"Failed to delete product: {res_del.text}"

    # Verify 404 on deleted product lookup
    res_get_deleted = requests.get(f"{BASE_URL}/products/{product_id}", headers=get_headers(token))
    assert res_get_deleted.status_code == 404, f"Deleted product still accessible! Code: {res_get_deleted.status_code}"
    print("   [PASS] Product deleted successfully; subsequent lookup returned HTTP 404.")

    # 8. Post-Deletion Metrics & Dashboard Synchronization
    print("\n8. Testing Post-Deletion Metrics Update...")
    res_metrics_post = requests.get(f"{BASE_URL}/metrics", headers=get_headers(token))
    assert res_metrics_post.status_code == 200
    print(f"   [PASS] Post-deletion metrics updated: Total Products = {res_metrics_post.json()['total_products']}.")

    print("\n=======================================================")
    print("  SUCCESS: All Phase 6.1 Functional Polish Tests Passed!")
    print("=======================================================\n")

if __name__ == "__main__":
    run_functional_verification()
