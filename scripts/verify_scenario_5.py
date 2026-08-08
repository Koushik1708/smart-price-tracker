import time
import requests
import sqlite3
import subprocess

API_URL = "http://localhost:8000"

def get_token():
    payload = {"username": "admin@letsgo.com", "password": "admin"}
    response = requests.post(f"{API_URL}/auth/login", data=payload)
    response.raise_for_status()
    return response.json()["access_token"]

def main():
    print("--- Scenario 5: Force a database commit failure ---")
    
    # We will simulate a commit failure by locking the database for sqlite
    # But since we use check_same_thread=False, it might just block.
    # A better way is to lock the DB exclusively in another process.
    
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    print("Locking database exclusively...")
    conn = sqlite3.connect("price_tracker.db", isolation_level="EXCLUSIVE")
    conn.execute("BEGIN EXCLUSIVE")
    
    try:
        # API request will now try to write to DB and fail (timeout)
        print("Sending API request... This should fail with a 500 internal server error or timeout")
        payload = {
            "url": "https://www.amazon.in/dp/B0CHX1W1XY",
            "target_price": 50000.0
        }
        try:
            response = requests.post(f"{API_URL}/products/track", json=payload, headers=headers, timeout=10)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Request failed: {e}")
            
    finally:
        print("Unlocking database...")
        conn.rollback()
        conn.close()

    print("Sending subsequent API request to ensure system recovered...")
    payload["url"] = "https://www.amazon.in/dp/B0CHX1W1ZZ" # different URL
    response = requests.post(f"{API_URL}/products/track", json=payload, headers=headers, timeout=10)
    print(f"Subsequent request status: {response.status_code}")
    print(f"Subsequent request response: {response.text}")
    assert response.status_code in [200, 409], "System did not recover properly!"
    print("System recovered successfully.")

if __name__ == "__main__":
    main()
