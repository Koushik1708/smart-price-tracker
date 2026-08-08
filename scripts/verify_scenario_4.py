import time
import requests
import threading

API_URL = "http://localhost:8000"

def get_token():
    payload = {"username": "admin@letsgo.com", "password": "admin"}
    response = requests.post(f"{API_URL}/auth/login", data=payload)
    response.raise_for_status()
    return response.json()["access_token"]

def track_product(token, url):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "url": url,
        "target_price": 50000.0
    }
    response = requests.post(f"{API_URL}/products/track", json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    return response

def main():
    print("--- Scenario 4: Start two concurrent scrape requests ---")
    token = get_token()
    url = f"https://www.amazon.in/dp/B0CHX1W1XY"
    
    # Thread 1
    t1 = threading.Thread(target=track_product, args=(token, url))
    # Thread 2
    t2 = threading.Thread(target=track_product, args=(token, url))
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()

if __name__ == "__main__":
    main()
