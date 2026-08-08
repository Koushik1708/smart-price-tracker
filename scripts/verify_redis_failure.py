import os
import requests
import time
import subprocess

API_URL = "http://localhost:8000"

def get_token():
    print("Getting token...")
    response = requests.post(
        f"{API_URL}/auth/login",
        data={"username": "admin@letsgo.com", "password": "admin"}
    )
    if response.status_code != 200:
        raise Exception(f"Login failed: {response.text}")
    return response.json()["access_token"]

def track_product(token):
    import uuid
    random_id = str(uuid.uuid4()).replace("-", "")[:10].upper()
    print("Calling /products/track...")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "url": f"https://www.amazon.in/dp/{random_id}",
        "target_price": 75000.0
    }
    return requests.post(f"{API_URL}/products/track", json=payload, headers=headers, timeout=120)

def main():
    token = get_token()
    
    print("\n--- Scenario 1: Stop Redis while the API is running ---")
    print("Stopping Redis...")
    subprocess.run(["docker", "stop", "redis-stack"], check=True)
    time.sleep(2)
    
    try:
        response = track_product(token)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        assert response.status_code == 503, f"Expected 503, got {response.status_code}"
        print("[PASS] API returned 503 when Redis is down.")
    finally:
        print("\n--- Scenario 2: Restart Redis ---")
        print("Starting Redis...")
        subprocess.run(["docker", "start", "redis-stack"], check=True)
        time.sleep(10)
        
    print("\nVerifying enqueue succeeds again...")
    response = track_product(token)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("[PASS] API successfully queued task after Redis restart.")

if __name__ == "__main__":
    main()
