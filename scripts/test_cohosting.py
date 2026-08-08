import subprocess
import time
import requests
import sys
import os

BASE_URL = "http://localhost:8005"
ENV = os.environ.copy()
ENV["PORT"] = "8005"
ENV["CELERY_BROKER_URL"] = "redis://localhost:6379/0"
ENV["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/0"
ENV["DATABASE_URL"] = "sqlite:///./price_tracker.db"
ENV["JWT_SECRET_KEY"] = "949f57d6e6a39a58b29c9b456bd84a7e289bf65db53049b49ab78c66e2c39e24"

def run_cohosting_test():
    print("=== Phase 2: Local Co-hosting Validation ===")
    
    # 1. Launch worker process
    print("Starting Celery worker (--pool=solo -c 1)...")
    worker_proc = subprocess.Popen(
        [sys.executable, "-m", "celery", "-A", "backend.celery_app:celery_app", "worker", "--loglevel=info", "--pool=solo", "-c", "1"],
        env=ENV
    )
    
    # 2. Launch FastAPI web server process
    print("Starting FastAPI web server (port 8005)...")
    web_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8005"],
        env=ENV
    )
    
    try:
        print("Waiting 4 seconds for co-hosted processes to initialize...")
        time.sleep(4)
        
        # Verify processes are alive
        assert worker_proc.poll() is None, "Celery worker process exited prematurely!"
        assert web_proc.poll() is None, "FastAPI web server process exited prematurely!"
        print("[OK] Both processes started and remain alive.")
        
        # 3. Test Health Endpoints
        print("\nTesting endpoints...")
        r_live = requests.get(f"{BASE_URL}/live", timeout=5)
        print(f"GET /live -> {r_live.status_code}: {r_live.json()}")
        assert r_live.status_code == 200
        
        r_ready = requests.get(f"{BASE_URL}/ready", timeout=5)
        print(f"GET /ready -> {r_ready.status_code}")
        assert r_ready.status_code == 200
        
        r_health = requests.get(f"{BASE_URL}/health", timeout=5)
        h_json = r_health.json()
        print(f"GET /health -> {r_health.status_code}: redis={h_json.get('redis')}, celery={h_json.get('celery')}, db={h_json.get('database')}")
        assert r_health.status_code == 200
        assert h_json["database"] == "healthy"
        assert h_json["redis"] == "healthy"
        assert h_json["celery"] == "healthy"
        
        r_ver = requests.get(f"{BASE_URL}/version", timeout=5)
        print(f"GET /version -> {r_ver.status_code}: {r_ver.json()}")
        assert r_ver.status_code == 200
        
        print("[OK] All health endpoints passed (200 OK).")
        
        # 4. Test User Auth & Task Enqueueing
        print("\nTesting Celery Task Execution...")
        email = f"cohost_user_{os.urandom(4).hex()}@example.com"
        reg_res = requests.post(f"{BASE_URL}/auth/register", json={"email": email, "password": "Password123!", "name": "CoHost Tester"})
        assert reg_res.status_code == 200
        
        login_res = requests.post(f"{BASE_URL}/auth/login", data={"username": email, "password": "Password123!"})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Track a product to enqueue task
        test_url = f"https://www.amazon.in/dp/{os.urandom(4).hex().upper()}1"
        track_res = requests.post(f"{BASE_URL}/products/track", json={"url": test_url}, headers=headers)
        assert track_res.status_code == 200
        prod_data = track_res.json()
        prod_id = prod_data["id"]
        print(f"Enqueued tracking task for product ID {prod_id} (status={prod_data['status']})")
        
        # Wait up to 10 seconds for Celery worker to consume & process task
        start_wait = time.time()
        final_status = prod_data['status']
        while time.time() - start_wait < 10:
            time.sleep(1)
            get_res = requests.get(f"{BASE_URL}/products/{prod_id}", headers=headers)
            if get_res.status_code == 200:
                p_status = get_res.json()["product"]["status"]
                final_status = p_status
                if p_status in ["SUCCESS", "FAILED"]:
                    break
                    
        print(f"Celery task execution finished. Final product status in DB: '{final_status}'")
        # In test mode without real internet/browser response, scraper can fail gracefully to FAILED, but it proves task executed!
        assert final_status in ["SUCCESS", "FAILED"], f"Task did not reach terminal state, stuck at {final_status}"
        print("[OK] Task was consumed and executed by Celery worker. PostgreSQL state updated.")
        
        # 5. Measure Process Memory
        print("\nMeasuring Memory Usage...")
        # Get memory via wmic/powershell/tasklist on Windows
        try:
            w_pid = worker_proc.pid
            u_pid = web_proc.pid
            out = subprocess.check_output(f'powershell "Get-Process -Id {w_pid},{u_pid} | Select-Object Id, ProcessName, WorkingSet64"', shell=True).decode()
            print("Process Working Sets (Bytes):\n" + out)
        except Exception as e:
            print(f"Memory check output error: {e}")
            
        print("[OK] Phase 2 Validation Complete!")
        
    finally:
        print("\nCleaning up processes...")
        worker_proc.terminate()
        web_proc.terminate()
        try:
            worker_proc.wait(timeout=3)
            web_proc.wait(timeout=3)
        except Exception:
            worker_proc.kill()
            web_proc.kill()
        print("Processes stopped.")

if __name__ == "__main__":
    run_cohosting_test()
