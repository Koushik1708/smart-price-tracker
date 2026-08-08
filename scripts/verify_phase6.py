import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import requests
import time

BASE_URL = os.getenv("BASE_URL", "http://localhost:8001")

def get_headers(token=None):
    headers = {"X-Forwarded-For": f"10.0.{os.urandom(1)[0]}.{os.urandom(1)[0]}"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def run_phase6_verification():
    print("\n=======================================================")
    print("      PHASE 6 ENTERPRISE SECURITY & ADMIN VERIFICATION")
    print("=======================================================\n")
    
    unique_suffix = os.urandom(4).hex()
    
    # 1. Register Normal User
    email_user = f"user_{unique_suffix}@example.com"
    res_reg_user = requests.post(f"{BASE_URL}/auth/register", json={"email": email_user, "password": "Password123!", "name": "Normal User"}, headers=get_headers())
    assert res_reg_user.status_code == 200, f"Failed to register normal user: {res_reg_user.text}"
    print("[OK] Normal user registered successfully.")
    
    login_user = requests.post(f"{BASE_URL}/auth/login", data={"username": email_user, "password": "Password123!"}, headers=get_headers()).json()
    token_user = login_user["access_token"]
    
    # 2. Login as Admin
    admin_password = "Password123!"
    admin_email = f"admin_{unique_suffix}@example.com"
    
    res_reg_admin = requests.post(f"{BASE_URL}/auth/register", json={"email": admin_email, "password": admin_password, "name": "Test Admin"}, headers=get_headers())
    assert res_reg_admin.status_code == 200, f"Failed to register test admin: {res_reg_admin.text}"
    admin_user_id = res_reg_admin.json()["id"]
    
    from backend.database import SessionLocal
    from backend.models import User
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == admin_user_id).first()
        if u:
            u.is_admin = True
            db.commit()
    finally:
        db.close()
        
    login_admin = requests.post(f"{BASE_URL}/auth/login", data={"username": admin_email, "password": admin_password}, headers=get_headers()).json()
    token_admin = login_admin["access_token"]
    print("[OK] Admin user authenticated successfully.")

    # 3. Test RBAC & Admin Endpoint Isolation
    print("\n--- Testing RBAC & Admin Endpoint Isolation ---")
    admin_endpoints = [
        "/admin/users",
        "/admin/products",
        "/admin/alerts",
        "/admin/workers",
        "/admin/queues",
        "/admin/redis",
        "/admin/failed-jobs",
        "/admin/diagnostics",
        "/admin/config",
        "/admin/stats",
        "/admin/audit-logs"
    ]
    
    for ep in admin_endpoints:
        # Test normal user access (should be 403 Forbidden)
        res = requests.get(f"{BASE_URL}{ep}", headers=get_headers(token_user))
        assert res.status_code == 403, f"SECURITY DEFECT: Normal user accessed admin endpoint {ep}! Status: {res.status_code}"
        
        # Test admin access (should be 200 OK)
        res_admin = requests.get(f"{BASE_URL}{ep}", headers=get_headers(token_admin))
        assert res_admin.status_code == 200, f"Admin failed to access endpoint {ep}! Status: {res_admin.status_code}, Response: {res_admin.text}"
        print(f"  [PASS] {ep}: User=403, Admin=200")
        
    print("[OK] All 11 /admin endpoints successfully verified: 403 for Normal Users, 200 for Admins.")

    # 4. Test Brute-Force Lockout Policy
    print("\n--- Testing Brute-Force Lockout Policy ---")
    lockout_email = f"lockout_{unique_suffix}@example.com"
    requests.post(f"{BASE_URL}/auth/register", json={"email": lockout_email, "password": "Password123!", "name": "Lockout User"}, headers=get_headers())
    
    lockout_ip_headers = get_headers()
    for attempt in range(1, 6):
        res_fail = requests.post(f"{BASE_URL}/auth/login", data={"username": lockout_email, "password": "WrongPassword!"}, headers=lockout_ip_headers)
        if attempt < 5:
            assert res_fail.status_code == 401, f"Attempt {attempt} expected 401, got {res_fail.status_code}"
            
    # 6th attempt must return 429 Account Locked
    res_locked = requests.post(f"{BASE_URL}/auth/login", data={"username": lockout_email, "password": "WrongPassword!"}, headers=lockout_ip_headers)
    assert res_locked.status_code == 429, f"Expected 429 Account Locked on 6th failed attempt, got {res_locked.status_code}: {res_locked.text}"
    print("[OK] Brute-Force Lockout correctly triggered 429 status on 5+ failed attempts.")

    # 5. Test Operational Limits
    print("\n--- Testing Operational Limits ---")
    res_limit = requests.get(f"{BASE_URL}/admin/config", headers=get_headers(token_admin)).json()
    assert "MAX_PRODUCTS_PER_USER" in res_limit
    assert "MAX_ALERTS_PER_USER" in res_limit
    print(f"[OK] Configured Operational Limits Verified: Max Products={res_limit['MAX_PRODUCTS_PER_USER']}, Max Alerts={res_limit['MAX_ALERTS_PER_USER']}")

    # 6. Test Immutable Audit Logging
    print("\n--- Testing Immutable Audit Trail ---")
    audit_res = requests.get(f"{BASE_URL}/admin/audit-logs", headers=get_headers(token_admin))
    assert audit_res.status_code == 200
    logs = audit_res.json()["audit_logs"]
    assert len(logs) > 0, "No audit logs recorded!"
    actions = [l["action"] for l in logs]
    print(f"[OK] Recorded Audit Actions found: {set(actions)}")
    assert "LOGIN" in actions or "USER_CREATED" in actions or "SECURITY_EVENT" in actions, "Expected core audit actions in log stream!"

    # 7. Test Security Headers
    print("\n--- Testing Security Headers ---")
    res_hdr = requests.get(f"{BASE_URL}/health", headers=get_headers())
    assert res_hdr.headers.get("X-Frame-Options") == "DENY", "X-Frame-Options missing or invalid"
    assert res_hdr.headers.get("X-Content-Type-Options") == "nosniff", "X-Content-Type-Options missing"
    assert res_hdr.headers.get("X-XSS-Protection") == "1; mode=block", "X-XSS-Protection missing"
    assert "Strict-Transport-Security" in res_hdr.headers, "Strict-Transport-Security missing"
    assert "Content-Security-Policy" in res_hdr.headers, "Content-Security-Policy missing"
    print("[OK] All 5 Security Headers verified (X-Frame-Options, X-Content-Type-Options, HSTS, CSP, XSS-Protection).")

    print("\n=======================================================")
    print("  SUCCESS: Phase 6 Enterprise Security & Admin Passed!")
    print("=======================================================\n")

if __name__ == "__main__":
    run_phase6_verification()
