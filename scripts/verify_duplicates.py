import requests
import os

BASE_URL = os.getenv("BASE_URL", "http://localhost:8001")

def run_tests():
    url = f"https://www.amazon.in/dp/{os.urandom(4).hex().upper()}1"
    
    # User A
    email_a = f"test_a_{os.urandom(4).hex()}@example.com"
    requests.post(f"{BASE_URL}/auth/register", json={"email": email_a, "password": "password", "name": "User A"})
    login_a = requests.post(f"{BASE_URL}/auth/login", data={"username": email_a, "password": "password"}).json()
    token_a = login_a["access_token"]
    
    # User B
    email_b = f"test_b_{os.urandom(4).hex()}@example.com"
    requests.post(f"{BASE_URL}/auth/register", json={"email": email_b, "password": "password", "name": "User B"})
    login_b = requests.post(f"{BASE_URL}/auth/login", data={"username": email_b, "password": "password"}).json()
    token_b = login_b["access_token"]
    
    print("Test A: User A tracks Product X")
    res_a1 = requests.post(f"{BASE_URL}/products/track", json={"url": url}, headers={"Authorization": f"Bearer {token_a}"})
    print(f"Status Code: {res_a1.status_code}")
    assert res_a1.status_code == 200, "Test A failed"
    
    print("Test B: User A tracks Product X again")
    res_a2 = requests.post(f"{BASE_URL}/products/track", json={"url": url}, headers={"Authorization": f"Bearer {token_a}"})
    print(f"Status Code: {res_a2.status_code}")
    assert res_a2.status_code == 409, "Test B failed"
    print(f"Response: {res_a2.text}")
    
    print("Test C: User B tracks Product X")
    res_b1 = requests.post(f"{BASE_URL}/products/track", json={"url": url}, headers={"Authorization": f"Bearer {token_b}"})
    print(f"Status Code: {res_b1.status_code}")
    assert res_b1.status_code == 200, "Test C failed"
    
    print("Test D: User B tracks Product X again")
    res_b2 = requests.post(f"{BASE_URL}/products/track", json={"url": url}, headers={"Authorization": f"Bearer {token_b}"})
    print(f"Status Code: {res_b2.status_code}")
    assert res_b2.status_code == 409, "Test D failed"
    
    print("Test E: Verify GET /products returns no duplicates")
    prods_a = requests.get(f"{BASE_URL}/products/search/", headers={"Authorization": f"Bearer {token_a}"}).json()["products"]
    prods_b = requests.get(f"{BASE_URL}/products/search/", headers={"Authorization": f"Bearer {token_b}"}).json()["products"]
    
    # We should have exactly 1 product tracking this URL for A, and 1 for B
    a_matches = [p for p in prods_a if url in p["url"]]
    b_matches = [p for p in prods_b if url in p["url"]]
    assert len(a_matches) == 1, "Duplicate found for A"
    assert len(b_matches) == 1, "Duplicate found for B"
    
    print("[SUCCESS] All duplicate tracking tests passed!")

if __name__ == "__main__":
    run_tests()
