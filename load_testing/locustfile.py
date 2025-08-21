"""
Load testing script for coupon system using Locust
Locust를 사용한 쿠폰 시스템 부하 테스트 스크립트
"""

from locust import HttpUser, task, between
import json
import random
import uuid
from datetime import datetime

class CouponUser(HttpUser):
    """
    User behavior for load testing coupon issuance system
    쿠폰 발급 시스템 부하 테스트를 위한 사용자 행동
    """
    wait_time = between(0.1, 0.5)  # Wait 0.1-0.5 seconds between requests
    
    def on_start(self):
        """Called when a user starts - initialize user data"""
        self.user_id = f"user_{uuid.uuid4().hex[:8]}"
        self.event_id = "load_test_event"
        
        # Check if system is healthy before starting
        response = self.client.get("/health")
        if response.status_code != 200:
            print(f"System health check failed: {response.status_code}")

    @task(80)  # 80% of requests are coupon issuance
    def issue_coupon(self):
        """Issue a coupon - main load testing task"""
        payload = {
            "user_id": self.user_id,
            "event_id": self.event_id
        }
        
        with self.client.post(
            "/api/v1/coupons/issue",
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    response.success()
                    print(f"✅ User {self.user_id} got coupon: {data.get('coupon_id')}")
                    print(f"   Remaining stock: {data.get('remaining_stock')}")
                else:
                    # Expected failures (user already participated, no stock)
                    if "already has a coupon" in data.get("message", ""):
                        response.success()  # This is expected behavior
                    elif "No coupons available" in data.get("message", ""):
                        response.success()  # This is expected when stock runs out
                        print("❌ No more coupons available")
                    else:
                        response.failure(f"Unexpected failure: {data.get('message')}")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(15)  # 15% of requests check event status
    def check_event_status(self):
        """Check event status"""
        with self.client.get(
            f"/api/v1/coupons/status/{self.event_id}",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                response.success()
                # Optionally log status for monitoring
                if random.random() < 0.1:  # Log 10% of status checks
                    print(f"📊 Event status - Stock: {data.get('remaining_stock')}, "
                          f"Participants: {data.get('total_participants')}")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(5)   # 5% of requests check user's coupon
    def check_user_coupon(self):
        """Check if user has a coupon"""
        with self.client.get(
            f"/api/v1/coupons/user/{self.user_id}/event/{self.event_id}",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


class AdminUser(HttpUser):
    """
    Admin user for testing admin endpoints
    관리자 엔드포인트 테스트를 위한 관리자 사용자
    """
    wait_time = between(5, 10)  # Less frequent requests
    weight = 1  # Much fewer admin users compared to regular users

    @task(70)
    def check_cache_stats(self):
        """Check cache statistics"""
        with self.client.get(
            "/api/v1/admin/cache/stats",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                if random.random() < 0.3:  # Log 30% of cache stats
                    data = response.json()
                    print(f"🔧 Cache stats: {data.get('redis_cluster_info', {})}")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(30)
    def initialize_new_event(self):
        """Initialize a new event (for testing)"""
        event_id = f"admin_test_event_{random.randint(1000, 9999)}"
        initial_stock = random.choice([100, 500, 1000, 2000])
        
        with self.client.post(
            f"/api/v1/admin/events/{event_id}/stock?initial_stock={initial_stock}",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "initialized successfully" in data.get("message", ""):
                    response.success()
                    print(f"🆕 Created event {event_id} with {initial_stock} stock")
                else:
                    response.success()  # Event already exists, which is fine
            else:
                response.failure(f"HTTP {response.status_code}")


class HighVolumeUser(HttpUser):
    """
    High volume user simulating the 1M user scenario
    100만 사용자 시나리오를 시뮬레이션하는 고볼륨 사용자
    """
    wait_time = between(0.01, 0.1)  # Very fast requests
    weight = 10  # More of these users for stress testing
    
    def on_start(self):
        """Initialize with unique user ID for each instance"""
        self.user_id = f"hv_user_{uuid.uuid4().hex}"
        self.event_id = "high_volume_event"

    @task(100)
    def rapid_coupon_requests(self):
        """Rapid coupon issuance requests"""
        payload = {
            "user_id": self.user_id,
            "event_id": self.event_id
        }
        
        start_time = datetime.now()
        
        with self.client.post(
            "/api/v1/coupons/issue",
            json=payload,
            catch_response=True
        ) as response:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    response.success()
                    if response_time > 100:  # Log slow responses
                        print(f"⚠️  Slow response: {response_time:.1f}ms for {self.user_id}")
                else:
                    response.success()  # Expected failures are OK
            elif response.status_code == 429:
                # Rate limiting is expected and OK
                response.success()
                print(f"🚦 Rate limited user: {self.user_id}")
            else:
                response.failure(f"HTTP {response.status_code}")


# Custom load testing scenarios
class ScenarioMixin:
    """Mixin for different load testing scenarios"""
    
    @staticmethod
    def setup_event_for_test(client, event_id: str, stock: int):
        """Helper to set up an event for testing"""
        response = client.post(f"/api/v1/admin/events/{event_id}/stock?initial_stock={stock}")
        return response.status_code == 200

# You can run specific scenarios with:
# locust -f locustfile.py --host=http://localhost CouponUser
# locust -f locustfile.py --host=http://localhost HighVolumeUser
# locust -f locustfile.py --host=http://localhost --users=1000 --spawn-rate=10