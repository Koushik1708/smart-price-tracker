import requests
import time
import sqlite3
import sys
import os

API_BASE = os.getenv("BASE_URL", "http://localhost:8001")
DB_PATH = "price_tracker.db"

def run_tests():
    print("Starting E2E Regression Tests...")
    
    # 0. User Registration and Auth setup
    email = f"regression_test_{os.urandom(4).hex()}@example.com"
    requests.post(f"{API_BASE}/auth/register", json={"email": email, "password": "password", "name": "Regression User"})
    login = requests.post(f"{API_BASE}/auth/login", data={"username": email, "password": "password"}).json()
    token = login["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n--- Pre-cleanup ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clean up test URL
    test_asin = "B0CHX1W1XY"
    test_url = f"https://www.amazon.in/dp/{test_asin}"
    cursor.execute("SELECT id FROM products WHERE product_id = ?", (test_asin,))
    rows = cursor.fetchall()
    for row in rows:
        requests.delete(f"{API_BASE}/products/{row[0]}", headers=headers)
        print(f"Pre-cleanup: deleted existing product {row[0]}")
    conn.close()

    # 1. Duplicate Handling & Status Lifecycle
    print("\n--- Test 1: Duplicate Handling & PENDING status ---")
    
    res1 = requests.post(f"{API_BASE}/products/track", json={"url": test_url}, headers=headers)
    assert res1.status_code == 200, f"Failed to track product: {res1.text}"
    prod1 = res1.json()
    
    print(f"Added product ID: {prod1['id']}, Status: {prod1['status']}")
    assert prod1['status'] == "PENDING", "Initial status should be PENDING"
    
    res2 = requests.post(f"{API_BASE}/products/track", json={"url": test_url}, headers=headers)
    assert res2.status_code == 409, f"Expected 409 on duplicate track, got {res2.status_code}"
    print("Duplicate handling passed.")
    
    # 2. Automatic Background Scraping & SUCCESS Status
    print("\n--- Test 2: Background Scraping & SUCCESS status ---")
    print("Waiting up to 25 seconds for background scraper to finish...")
    success = False
    for i in range(25):
        time.sleep(1)
        res = requests.get(f"{API_BASE}/products/{prod1['id']}", headers=headers)
        data = res.json()
        status = data['product']['status']
        if status == 'SUCCESS':
            success = True
            print("Product successfully scraped!")
            assert data['product']['title'] != "Tracking Pending...", "Title was not updated."
            assert len(data['history']) > 0, "No price history created."
            break
        elif status == 'FAILED':
            print("Scraping failed unexpectedly.")
            sys.exit(1)
    
    assert success, "Product scraping timed out or didn't reach SUCCESS state."
    
    # 3. Failure Recovery
    print("\n--- Test 3: Failure Recovery ---")
    bad_url = "https://www.amazon.in/dp/B000000000" # Dummy ASIN
    res_bad = requests.post(f"{API_BASE}/products/track", json={"url": bad_url}, headers=headers)
    prod_bad = res_bad.json()
    print(f"Added invalid product ID: {prod_bad['id']}")
    
    failed = False
    for i in range(20):
        time.sleep(1)
        res = requests.get(f"{API_BASE}/products/{prod_bad['id']}", headers=headers)
        data = res.json()
        status = data['product']['status']
        if status == 'FAILED':
            failed = True
            print("Product correctly marked as FAILED.")
            break
    
    assert failed, "Invalid product did not reach FAILED state."
    
    # 4. Deletion & Cascade
    print("\n--- Test 4: Transactional Deletion ---")
    del_res = requests.delete(f"{API_BASE}/products/{prod1['id']}", headers=headers)
    assert del_res.status_code == 200, "Delete API failed."
    
    # Check API
    check_res = requests.get(f"{API_BASE}/products/{prod1['id']}", headers=headers)
    assert check_res.status_code == 404, "Product still exists in API after deletion."
    
    # Check DB Cascade
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM products WHERE id = ?", (prod1['id'],))
    assert cursor.fetchone()[0] == 0, "Product still in database."
    
    cursor.execute("SELECT count(*) FROM price_snapshots WHERE product_id = ?", (prod1['id'],))
    assert cursor.fetchone()[0] == 0, "Price snapshots were not deleted (cascade failed)."
    
    print("Transactional deletion passed.")
    
    print("\nAll E2E Regression Tests Passed Successfully!")

if __name__ == "__main__":
    run_tests()
