import time
import requests
import sqlite3
import subprocess
import random

API_URL = "http://localhost:8000"

def get_token():
    payload = {"username": "admin@letsgo.com", "password": "admin"}
    response = requests.post(f"{API_URL}/auth/login", data=payload)
    response.raise_for_status()
    return response.json()["access_token"]

def main():
    print("--- Scenario 3: Kill the Celery worker during an active scrape ---")
    
    # 1. Start Celery worker in background
    print("Starting Celery worker...")
    worker_proc = subprocess.Popen(
        [r".\venv\Scripts\celery.exe", "-A", "backend.celery_app", "worker", "--loglevel=info", "-P", "solo"],
        shell=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )
    time.sleep(5) # wait for worker to initialize

    # 2. Queue a job
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    random_id = f"KIL{random.randint(1000, 9999)}"
    payload = {
        "url": f"https://www.amazon.in/dp/{random_id}",
        "target_price": 50000.0
    }
    print(f"Queuing product track for {random_id}...")
    response = requests.post(f"{API_URL}/products/track", json=payload, headers=headers)
    assert response.status_code == 200
    product = response.json()
    product_id = product["id"]
    
    print(f"Product queued with internal ID {product_id}. Waiting 1 second for scrape to begin...")
    time.sleep(1)
    
    # 3. Kill Celery worker abruptly
    print("Killing Celery worker abruptly...")
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(worker_proc.pid)], check=False)
    # also kill any lingering Python processes named celery
    subprocess.run(["taskkill", "/F", "/IM", "celery.exe"], check=False)
    
    print("Worker killed. Wait 3 seconds...")
    time.sleep(3)
    
    # 4. Restart Celery worker
    print("Restarting Celery worker...")
    worker_proc_2 = subprocess.Popen(
        [r".\venv\Scripts\celery.exe", "-A", "backend.celery_app", "worker", "--loglevel=info", "-P", "solo"],
        shell=True
    )
    
    # 5. Check if the task was retried and completed
    print("Waiting 15 seconds for retry to complete...")
    for _ in range(15):
        time.sleep(1)
        # Check DB
        conn = sqlite3.connect("price_tracker.db")
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM products WHERE id=?", (product_id,))
        status = cursor.fetchone()[0]
        conn.close()
        
        if status in ['TRACKING', 'FAILED']:
            print(f"Task completed with status: {status}")
            break
            
    print("Cleaning up...")
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(worker_proc_2.pid)], check=False)

if __name__ == "__main__":
    main()
