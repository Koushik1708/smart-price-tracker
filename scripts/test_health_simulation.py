import os
import sys
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

def run_simulation_tests():
    print("--- Simulation Test 1: Normal / High RAM (Degraded, HTTP 200) ---")
    with patch("psutil.virtual_memory") as mock_mem:
        mock_mem.return_value = MagicMock(percent=95.0, available=1024*1024*500)
        response = client.get("/health")
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Status: {data['status']}, Summary: {data.get('summary')}")
        print(f"Memory Object: {data.get('memory')}")
        assert response.status_code == 200, "High RAM should return HTTP 200"
        assert data["status"] == "degraded", "High RAM should return degraded"
        assert data["memory"]["status"] == "warning", "Memory status should be warning"
        print("[OK] High RAM Simulation Passed.")

    print("\n--- Simulation Test 2: Database Outage (Unhealthy, HTTP 503) ---")
    with patch("sqlalchemy.orm.Session.execute", side_effect=Exception("DB Connection Refused")):
        response = client.get("/health")
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Status: {data['status']}, Summary: {data.get('summary')}")
        assert response.status_code == 503, "DB Outage must return HTTP 503"
        assert data["status"] == "unhealthy", "DB Outage must return unhealthy"
        print("[OK] Database Outage Simulation Passed.")

    print("\n--- Simulation Test 3: Redis Outage (Unhealthy, HTTP 503) ---")
    with patch("redis.Redis.from_url", side_effect=Exception("Redis Unavailable")):
        response = client.get("/health")
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Status: {data['status']}, Summary: {data.get('summary')}")
        assert response.status_code == 503, "Redis Outage must return HTTP 503"
        assert data["status"] == "unhealthy", "Redis Outage must return unhealthy"
        print("[OK] Redis Outage Simulation Passed.")

    print("\n--- Simulation Test 4: Fully Healthy System (Healthy, HTTP 200) ---")
    with patch("psutil.virtual_memory") as mock_mem, \
         patch("shutil.disk_usage") as mock_disk:
        mock_mem.return_value = MagicMock(percent=45.0, available=1024*1024*8000)
        mock_disk.return_value = (100*1024*1024*1024, 50*1024*1024*1024, 50*1024*1024*1024) # 50% free
        response = client.get("/health")
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Status: {data['status']}, Summary: {data.get('summary')}")
        assert response.status_code == 200, "Healthy system must return HTTP 200"
        assert data["status"] == "healthy", "Healthy system status must be healthy"
        print("[OK] Fully Healthy System Simulation Passed.")

if __name__ == "__main__":
    run_simulation_tests()
