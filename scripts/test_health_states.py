import requests
import os
import sys

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

def test_health_classification():
    print("--- 1. Testing Normal Endpoint GET /health ---")
    try:
        r = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {r.status_code}")
        data = r.json()
        print(f"Overall Status: {data.get('status')}")
        print(f"Database: {data.get('database')}")
        print(f"Redis: {data.get('redis')}")
        print(f"Celery: {data.get('celery')}")
        print(f"Memory: {data.get('memory')}")
        print(f"Disk: {data.get('disk')}")
        print(f"CPU: {data.get('cpu')}")
        print(f"Queue: {data.get('queue')}")
        
        # Verify status is valid (healthy or degraded if memory is currently >90%)
        assert data.get('status') in ['healthy', 'degraded', 'unhealthy'], "Invalid status returned"
        print("[SUCCESS] Backend health endpoint responded with structured status classification.")
    except Exception as e:
        print(f"[FAIL] Backend unreachable: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_health_classification()
