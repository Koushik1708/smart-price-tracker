import os
import sys
import time
import subprocess
import requests
import psutil
import sqlite3

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
DB_PATH = "price_tracker.db"

def get_celery_pids():
    pids = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = proc.info['cmdline']
            if cmd and any('celery' in part.lower() for part in cmd):
                pids.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return pids

def run_test():
    print("Starting Worker Recovery Test...")
    
    # 1. Kill any existing Celery workers first to start clean
    print("Cleaning up any existing Celery workers...")
    pids = get_celery_pids()
    for pid in pids:
        try:
            p = psutil.Process(pid)
            p.kill()
        except Exception:
            pass
    time.sleep(2)

    # 2. Start fresh Celery worker with short visibility timeout
    print("Starting initial Celery worker with short visibility timeout...")
    venv_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    celery_bin = os.path.join(venv_dir, "venv", "Scripts", "celery.exe")
    cmd = [
        celery_bin if os.path.exists(celery_bin) else "celery",
        "-A", "backend.celery_app:celery_app",
        "worker",
        "--loglevel=info",
        "--pool=solo"
    ]
    env = os.environ.copy()
    env["CELERY_VISIBILITY_TIMEOUT"] = "5"
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    time.sleep(4) # Wait for worker to ready

    # 3. Register/Login
    email = f"recovery_test_{os.urandom(4).hex()}@example.com"
    requests.post(f"{BASE_URL}/auth/register", json={"email": email, "password": "password", "name": "Recovery User"})
    login = requests.post(f"{BASE_URL}/auth/login", data={"username": email, "password": "password"}).json()
    token = login["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Use a product that is not currently tracked
    test_asin = "B0CHX1W1XY"
    test_url = f"https://www.amazon.in/dp/{test_asin}"
    
    # Clean it from DB first
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE product_id = ?", (test_asin,))
    conn.commit()
    conn.close()

    print("Adding product...")
    res = requests.post(f"{BASE_URL}/products/track", json={"url": test_url}, headers=headers)
    assert res.status_code == 200, f"Failed to track: {res.text}"
    prod = res.json()
    prod_id = prod["id"]
    print(f"Product tracked. ID: {prod_id}")

    # Wait for the status to become SCRAPING
    print("Waiting for status to become SCRAPING...")
    scraping_reached = False
    for _ in range(30):
        time.sleep(0.5)
        status_res = requests.get(f"{BASE_URL}/products/{prod_id}", headers=headers).json()
        status = status_res["product"]["status"]
        if status == "SCRAPING":
            scraping_reached = True
            break
        elif status in ["SUCCESS", "FAILED"]:
            print(f"Scrape already finished with status: {status}")
            scraping_reached = True
            break

    if not scraping_reached:
        print("ERROR: Task did not reach SCRAPING state in time.")
        sys.exit(1)

    # 4. Immediately terminate/kill the Celery worker process
    print("Terminating Celery worker processes mid-scrape...")
    active_pids = get_celery_pids()
    for pid in active_pids:
        try:
            p = psutil.Process(pid)
            p.kill()
            print(f"Killed Celery PID {pid}")
        except Exception as e:
            print(f"Failed to kill PID {pid}: {e}")
    time.sleep(2)

    # Verify in DB that it is still in SCRAPING or PENDING state
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM products WHERE id = ?", (prod_id,))
    db_status = cursor.fetchone()[0]
    conn.close()
    print(f"Current DB status after worker crash: {db_status}")
    assert db_status in ["SCRAPING", "PENDING"], f"Expected SCRAPING or PENDING, got {db_status}"

    # 5. Restart Celery worker
    print("Restarting Celery worker...")
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    print("Celery worker restarted.")

    # 6. Wait for the task to be picked up and finish
    print("Waiting for task recovery and completion...")
    success = False
    for _ in range(45):
        time.sleep(1)
        status_res = requests.get(f"{BASE_URL}/products/{prod_id}", headers=headers).json()
        status = status_res["product"]["status"]
        if status in ["SUCCESS", "FAILED"]:
            success = True
            print(f"Recovery SUCCESS! Final status: {status}")
            break

    # Cleanup: stop worker
    final_pids = get_celery_pids()
    for pid in final_pids:
        try:
            psutil.Process(pid).kill()
        except Exception:
            pass

    if not success:
        print("ERROR: Task was not recovered/completed after worker restart.")
        sys.exit(1)

    print("[SUCCESS] Celery worker recovery test passed!")

if __name__ == "__main__":
    run_test()
