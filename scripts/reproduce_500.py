import requests
import os
import sqlite3

BASE_URL = "http://localhost:8001"

def reproduce():
    # Find an existing URL in the DB
    conn = sqlite3.connect('price_tracker.db')
    row = conn.execute("SELECT url FROM products LIMIT 1").fetchone()
    if not row:
        print("No products in DB!")
        return
    url = row[0]
    
    # 1. Create a user
    email = f"test_{os.urandom(4).hex()}@example.com"
    requests.post(f"{BASE_URL}/auth/register", json={"email": email, "password": "password", "name": "Test User"})
    
    # 2. Login
    login_res = requests.post(f"{BASE_URL}/auth/login", data={"username": email, "password": "password"})
    token = login_res.json()["access_token"]
    
    print(f"Tracking {url} with new user...")
    
    res = requests.post(f"{BASE_URL}/products/track", json={"url": url}, headers={"Authorization": f"Bearer {token}"})
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.text}")

if __name__ == "__main__":
    reproduce()
