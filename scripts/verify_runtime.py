import subprocess
import time
import requests
import json
import os
import sys

BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"

def print_step(msg):
    print(f"\n{'='*50}\n[STEP] {msg}\n{'='*50}")

def start_services():
    print_step("Starting Services (Backend, Celery, Frontend)")
    # Start Backend
    backend = subprocess.Popen([r"venv\Scripts\uvicorn", "backend.main:app", "--port", "8000"], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Start Celery
    celery = subprocess.Popen([r"venv\Scripts\celery", "-A", "backend.celery_app", "worker", "-l", "INFO"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Start Frontend (Assuming npm run dev)
    frontend = subprocess.Popen(["npm", "run", "dev"], cwd="frontend", shell=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Ensure Redis is running
    subprocess.run(["docker", "start", "redis-stack"], stdout=subprocess.DEVNULL)
    
    print("Waiting for services to initialize...")
    time.sleep(15)
    return backend, celery, frontend

def stop_services(processes):
    print_step("Stopping Services")
    for p in processes:
        if p:
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    p.terminate()
            except:
                pass

def login_user(email, password):
    print(f"Logging in user: {email}")
    resp = requests.post(f"{BASE_URL}/auth/login", data={"username": email, "password": password})
    if resp.status_code == 200:
        return resp.json().get("access_token")
    
    # Try alternate login if it's not OAuth2PasswordRequestForm
    resp2 = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if resp2.status_code == 200:
        return resp2.cookies.get("session") or resp2.json().get("access_token")
        
    print(f"Login failed: {resp.status_code} - {resp.text} and {resp2.status_code} - {resp2.text}")
    return None

def fetch_dashboard_endpoint(token, endpoint):
    headers = {"Authorization": f"Bearer {token}"}
    start = time.time()
    try:
        resp = requests.get(f"{BASE_URL}/dashboard/{endpoint}", headers=headers)
        duration = (time.time() - start) * 1000
        print(f"GET /dashboard/{endpoint} - Status: {resp.status_code} - Time: {duration:.2f}ms")
        return resp, duration
    except Exception as e:
        print(f"GET /dashboard/{endpoint} - Error: {e}")
        return None, 0

def run_tests():
    backend, celery, frontend = None, None, None
    try:
        backend, celery, frontend = start_services()
        
        # Test Frontend Render
        print_step("Verify Dashboard Renders (Frontend Check)")
        try:
            f_resp = requests.get(FRONTEND_URL)
            print(f"Frontend Status: {f_resp.status_code}")
        except Exception as e:
            print(f"Frontend failed: {e}")

        # Seed data to ensure admin exists
        print_step("Running seed_data.py to ensure admin exists")
        subprocess.run([sys.executable, "scripts/seed_data.py"], stdout=subprocess.DEVNULL)

        print_step("Creating empty user")
        empty_email = f"empty_{int(time.time())}@example.com"
        requests.post(f"{BASE_URL}/auth/register", json={"email": empty_email, "password": "password", "name": "Empty"})
        
        empty_token = login_user(empty_email, "password")
        existing_token = login_user("admin@letsgo.com", "admin")
        
        endpoints = ["summary", "activity", "price-drops", "recent-products"]
        results = {}
        
        print_step("Testing Endpoints - Empty User")
        results["empty_user"] = {}
        if empty_token:
            for ep in endpoints:
                resp, dur = fetch_dashboard_endpoint(empty_token, ep)
                if resp:
                    results["empty_user"][ep] = {"status": resp.status_code, "data": resp.json() if resp.status_code == 200 else None, "time_ms": dur}
        
        print_step("Testing Endpoints - Existing User")
        results["existing_user"] = {}
        if existing_token:
            for ep in endpoints:
                resp, dur = fetch_dashboard_endpoint(existing_token, ep)
                if resp:
                    results["existing_user"][ep] = {"status": resp.status_code, "data": resp.json() if resp.status_code == 200 else None, "time_ms": dur}

        print_step("Testing Redis Failure Downgrade")
        # Stop Redis
        subprocess.run(["docker", "stop", "redis-stack"])
        time.sleep(3) # give it a moment
        
        results["redis_down"] = {}
        if existing_token:
            for ep in endpoints:
                resp, dur = fetch_dashboard_endpoint(existing_token, ep)
                if resp:
                    results["redis_down"][ep] = {"status": resp.status_code, "data": resp.json() if resp.status_code == 200 else None, "time_ms": dur}
            
        # Start Redis back up
        subprocess.run(["docker", "start", "redis-stack"])
        
        print_step("Running Regression Suite")
        regression = subprocess.run([r"venv\Scripts\pytest", "tests/"], capture_output=True, text=True)
        results["regression"] = {"returncode": regression.returncode, "stdout": regression.stdout, "stderr": regression.stderr}
        print(f"Regression tests return code: {regression.returncode}")
        
        with open("validation_results.json", "w") as f:
            json.dump(results, f, indent=2)
            
        print("Done. Results saved to validation_results.json")
        
    finally:
        stop_services([backend, celery, frontend])
        subprocess.run(["docker", "start", "redis-stack"], stdout=subprocess.DEVNULL) # Ensure redis is up

if __name__ == "__main__":
    run_tests()
