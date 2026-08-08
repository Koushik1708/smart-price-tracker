from locust import HttpUser, task, between
import uuid

class PriceTrackerUser(HttpUser):
    wait_time = between(1, 5)
    
    def on_start(self):
        # Authenticate / Register a unique user for this session
        self.email = f"loadtest_{uuid.uuid4().hex[:8]}@example.com"
        self.password = "password"
        
        # Register
        self.client.post("/auth/register", json={
            "email": self.email,
            "password": self.password,
            "name": "Load Test User"
        })
        
        # Login
        response = self.client.post("/auth/login", data={
            "username": self.email,
            "password": self.password
        })
        
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            self.headers = {}

    @task(5)
    def view_dashboard(self):
        if not self.headers:
            return
        # Get dashboard endpoints
        self.client.get("/dashboard/summary", headers=self.headers)
        self.client.get("/dashboard/activity", headers=self.headers)
        self.client.get("/dashboard/recent-products", headers=self.headers)
        self.client.get("/dashboard/price-drops", headers=self.headers)

    @task(3)
    def check_health(self):
        self.client.get("/health")
        self.client.get("/ready")
        self.client.get("/live")

    @task(1)
    def track_product(self):
        if not self.headers:
            return
        dummy_asin = f"B0{uuid.uuid4().hex[:8].upper()}"
        self.client.post("/products/track", json={
            "url": f"https://www.amazon.in/dp/{dummy_asin}"
        }, headers=self.headers)
