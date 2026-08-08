from fastapi.testclient import TestClient
from backend.main import app
from backend.auth import create_access_token
from backend.database import get_db, SessionLocal
from backend.models import User
import time

def get_test_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = get_test_db

client = TestClient(app)

db = SessionLocal()
user = db.query(User).filter(User.email == "admin@letsgo.com").first()
db.close()

if user:
    token = create_access_token({"sub": user.email})
    response = client.get("/dashboard/activity", headers={"Authorization": f"Bearer {token}"})
    print("Status:", response.status_code)
    print("Body:", response.text)
else:
    print("Admin user not found")
