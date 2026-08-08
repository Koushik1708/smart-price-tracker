import time
import requests
import subprocess
import os

API_URL = "http://localhost:8000"

def get_token():
    payload = {"username": "admin@letsgo.com", "password": "admin"}
    response = requests.post(f"{API_URL}/auth/login", data=payload)
    response.raise_for_status()
    return response.json()["access_token"]

def main():
    print("--- Scenario 6: Playwright Timeout ---")
    
    # 1. Start Celery worker in background with a 1ms timeout!
    env = os.environ.copy()
    env["PLAYWRIGHT_TIMEOUT"] = "1"
    
    print("Starting Celery worker with 1ms Playwright timeout...")
    worker_proc = subprocess.Popen(
        [r".\venv\Scripts\celery.exe", "-A", "backend.celery_app", "worker", "--loglevel=info", "-P", "solo"],
        shell=True,
        env=env
    )
    time.sleep(5) # wait for worker to initialize

    # 2. Queue a job
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    import random
    random_id = f"KIL{random.randint(1000, 9999)}"
    payload = {
        "url": f"https://www.amazon.in/dp/{random_id}",
        "target_price": 50000.0
    }
    print(f"Queuing product track...")
    response = requests.post(f"{API_URL}/products/track", json=payload, headers=headers)
    assert response.status_code == 200
    
    print(f"Waiting 10 seconds for worker to process and fail with timeout...")
    time.sleep(10)
    
    # Check for orphan node processes
    print("Checking for orphan Chromium/node processes...")
    try:
        output = subprocess.check_output('tasklist /FI "IMAGENAME eq node.exe"', shell=True).decode()
        if "node.exe" in output:
            print("WARNING: Orphan node/playwright processes found!")
            print(output)
        else:
            print("No orphan node processes found. Cleanup successful.")
    except subprocess.CalledProcessError:
        print("No orphan node processes found.")

    print("Cleaning up...")
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(worker_proc.pid)], check=False)

if __name__ == "__main__":
    main()
