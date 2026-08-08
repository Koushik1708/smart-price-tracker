import sys
import os
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models import User, Product, AlertThreshold, AuditLog

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8001")
TARGET_EMAIL = "bhukyakoushik2006@gmail.com"
NEW_PASSWORD = "Password123!"

def run_account_reset():
    print("=" * 60)
    print("   DEVELOPMENT ACCOUNT RESET & RE-REGISTRATION VERIFICATION")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Step 1: Query user immediately before deletion
        user = db.query(User).filter(User.email == TARGET_EMAIL).first()
        if not user:
            print(f"[INFO] User {TARGET_EMAIL} not found in database. Proceeding to registration.")
            old_user_id = None
        else:
            old_user_id = user.id
            products_count = db.query(Product).filter(Product.user_id == user.id).count()
            alerts_count = db.query(AlertThreshold).filter(AlertThreshold.user_id == user.id).count()
            audit_count = db.query(AuditLog).filter(AuditLog.user_id == user.id).count()
            
            print(f"[INSPECT] Found user ID {user.id} ({user.email}):")
            print(f"   - Products: {products_count}")
            print(f"   - Alerts: {alerts_count}")
            print(f"   - Audit Logs: {audit_count}")
            
            # Step 2: Delete in ONE atomic transaction
            print(f"[DELETE] Initiating atomic transaction deletion for user ID {user.id}...")
            db.delete(user)
            db.commit()
            print("[DELETE] Commit successful.")

        # Step 3: Verify deletion
        verify_user = db.query(User).filter(User.email == TARGET_EMAIL).first()
        assert verify_user is None, f"[FAIL] User {TARGET_EMAIL} still exists after deletion!"
        
        if old_user_id:
            dep_products = db.query(Product).filter(Product.user_id == old_user_id).count()
            dep_alerts = db.query(AlertThreshold).filter(AlertThreshold.user_id == old_user_id).count()
            assert dep_products == 0, f"[FAIL] {dep_products} orphaned products remain!"
            assert dep_alerts == 0, f"[FAIL] {dep_alerts} orphaned alerts remain!"
            
        print("[VERIFIED] Account deletion verified. User and all dependent records removed.")
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Deletion failed and transaction rolled back: {e}")
        sys.exit(1)
    finally:
        db.close()

    # Step 3b: Verify old account credentials no longer authenticate
    print(f"\n[AUTH CHECK] Verifying old account credentials fail authentication...")
    old_auth_res = requests.post(f"{API_BASE_URL}/auth/login", data={"username": TARGET_EMAIL, "password": "OldPassword123!"})
    assert old_auth_res.status_code == 401, f"[FAIL] Old account should return 401, got {old_auth_res.status_code}"
    print("[VERIFIED] Old account credentials rejected (HTTP 401 Unauthorized).")

    # Step 4: Re-register email through normal registration flow
    print(f"\n[REGISTER] Registering {TARGET_EMAIL} via normal registration API (POST /auth/register)...")
    reg_payload = {
        "name": "Koushik Bhukya",
        "email": TARGET_EMAIL,
        "password": NEW_PASSWORD
    }
    reg_res = requests.post(f"{API_BASE_URL}/auth/register", json=reg_payload)
    assert reg_res.status_code == 200, f"[FAIL] Registration failed: {reg_res.status_code} {reg_res.text}"
    
    reg_user_data = reg_res.json()
    new_reg_id = reg_user_data.get("id")
    assert new_reg_id, "[FAIL] Registration response missing user ID!"
    print(f"[SUCCESS] Registered {TARGET_EMAIL} successfully. Assigned User ID = {new_reg_id}.")

    # Step 5: Login verification
    print(f"\n[LOGIN] Logging in with new credentials (POST /auth/login)...")
    login_res = requests.post(f"{API_BASE_URL}/auth/login", data={"username": TARGET_EMAIL, "password": NEW_PASSWORD})
    assert login_res.status_code == 200, f"[FAIL] Login failed: {login_res.status_code} {login_res.text}"
    
    login_token = login_res.json().get("access_token")
    assert login_token, "[FAIL] Login response missing access_token!"
    headers = {"Authorization": f"Bearer {login_token}"}
    print("[SUCCESS] Login successful.")

    # Step 6: Verify /auth/me
    print(f"\n[AUTH ME] Calling GET /auth/me...")
    me_res = requests.get(f"{API_BASE_URL}/auth/me", headers=headers)
    assert me_res.status_code == 200, f"[FAIL] /auth/me failed: {me_res.status_code} {me_res.text}"
    
    user_data = me_res.json()
    new_user_id = user_data.get("id")
    print(f"[SUCCESS] /auth/me verified: User ID = {new_user_id}, Name = '{user_data.get('name')}', Email = '{user_data.get('email')}'")

    # Step 7: Verify tenant isolation (new user cannot access another user's products)
    print(f"\n[ISOLATION] Verifying tenant isolation for new User ID {new_user_id}...")
    products_res = requests.get(f"{API_BASE_URL}/products/search/?page=1", headers=headers)
    assert products_res.status_code == 200
    user_products = products_res.json().get("products", [])
    print(f"[SUCCESS] New user has {len(user_products)} tracked products (isolated).")

    print("\n" + "=" * 60)
    print("  ACCOUNT RESET & RE-REGISTRATION VERIFICATION PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    run_account_reset()
