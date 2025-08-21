"""
Stress testing script for coupon system with concurrent requests
동시 요청을 사용한 쿠폰 시스템 스트레스 테스트 스크립트
"""

import asyncio
import aiohttp
import time
import random
import uuid
from concurrent.futures import ThreadPoolExecutor
import threading
from collections import defaultdict
import json

class CouponStressTest:
    """Stress test for coupon issuance system"""
    
    def __init__(self, base_url="http://localhost", concurrent_users=1000):
        self.base_url = base_url
        self.concurrent_users = concurrent_users
        self.results = defaultdict(int)
        self.response_times = []
        self.lock = threading.Lock()
        
    async def issue_coupon_request(self, session, user_id, event_id="stress_test_event"):
        """Single coupon issuance request"""
        payload = {
            "user_id": user_id,
            "event_id": event_id
        }
        
        start_time = time.time()
        try:
            async with session.post(
                f"{self.base_url}/api/v1/coupons/issue",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                with self.lock:
                    self.response_times.append(response_time)
                
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        with self.lock:
                            self.results["success"] += 1
                        return {"status": "success", "coupon_id": data.get("coupon_id"), "response_time": response_time}
                    else:
                        with self.lock:
                            self.results[data.get("message", "unknown_error")] += 1
                        return {"status": "failed", "reason": data.get("message"), "response_time": response_time}
                else:
                    with self.lock:
                        self.results[f"http_{response.status}"] += 1
                    return {"status": "http_error", "code": response.status, "response_time": response_time}
                    
        except asyncio.TimeoutError:
            with self.lock:
                self.results["timeout"] += 1
            return {"status": "timeout", "response_time": 30000}
        except Exception as e:
            with self.lock:
                self.results["error"] += 1
            return {"status": "error", "error": str(e), "response_time": 0}

    async def run_concurrent_test(self, event_id="stress_test_event", target_stock=1000):
        """Run concurrent stress test"""
        print(f"🚀 Starting stress test with {self.concurrent_users} concurrent users")
        print(f"   Target: {target_stock} coupons for event '{event_id}'")
        
        # Initialize event stock
        async with aiohttp.ClientSession() as session:
            init_url = f"{self.base_url}/api/v1/admin/events/{event_id}/stock?initial_stock={target_stock}"
            async with session.post(init_url) as response:
                if response.status == 200:
                    print(f"✅ Event '{event_id}' initialized with {target_stock} coupons")
                else:
                    print(f"⚠️  Event initialization returned: {response.status}")
        
        # Generate unique user IDs
        user_ids = [f"stress_user_{uuid.uuid4().hex[:8]}" for _ in range(self.concurrent_users)]
        
        start_time = time.time()
        
        # Run concurrent requests
        connector = aiohttp.TCPConnector(limit=None, limit_per_host=None)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [
                self.issue_coupon_request(session, user_id, event_id)
                for user_id in user_ids
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze results
        self.print_results(total_time)
        
        return self.results

    def print_results(self, total_time):
        """Print detailed test results"""
        print("\n" + "="*50)
        print("🎯 STRESS TEST RESULTS")
        print("="*50)
        
        total_requests = sum(self.results.values())
        success_rate = (self.results["success"] / total_requests * 100) if total_requests > 0 else 0
        
        print(f"Total Requests: {total_requests}")
        print(f"Total Time: {total_time:.2f} seconds")
        print(f"Requests/Second: {total_requests/total_time:.2f}")
        print(f"Success Rate: {success_rate:.2f}%")
        print(f"Successful Coupons: {self.results['success']}")
        
        print("\n📊 Response Time Statistics:")
        if self.response_times:
            self.response_times.sort()
            print(f"  Min: {min(self.response_times):.1f}ms")
            print(f"  Max: {max(self.response_times):.1f}ms")
            print(f"  Avg: {sum(self.response_times)/len(self.response_times):.1f}ms")
            print(f"  P50: {self.response_times[len(self.response_times)//2]:.1f}ms")
            print(f"  P95: {self.response_times[int(len(self.response_times)*0.95)]:.1f}ms")
            print(f"  P99: {self.response_times[int(len(self.response_times)*0.99)]:.1f}ms")
        
        print("\n🔍 Detailed Results:")
        for result_type, count in sorted(self.results.items()):
            percentage = (count / total_requests * 100) if total_requests > 0 else 0
            print(f"  {result_type}: {count} ({percentage:.1f}%)")
            
        print("\n" + "="*50)

    async def check_system_health(self):
        """Check if system is healthy before testing"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ System health: {data.get('status')}")
                        return True
                    else:
                        print(f"❌ Health check failed: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False

    async def run_gradual_load_test(self, max_users=1000, step=100, step_duration=30):
        """Run gradual load increase test"""
        print(f"🔄 Starting gradual load test: 0 → {max_users} users")
        
        if not await self.check_system_health():
            print("❌ System health check failed. Aborting test.")
            return
        
        for current_users in range(step, max_users + 1, step):
            print(f"\n📈 Testing with {current_users} concurrent users...")
            
            # Reset results for this step
            self.results.clear()
            self.response_times.clear()
            
            # Run test with current user count
            self.concurrent_users = current_users
            await self.run_concurrent_test(
                event_id=f"gradual_test_{current_users}",
                target_stock=min(1000, current_users)
            )
            
            # Brief pause between steps
            if current_users < max_users:
                print(f"⏳ Waiting {step_duration} seconds before next step...")
                await asyncio.sleep(step_duration)


async def main():
    """Main function to run stress tests"""
    print("🎯 Coupon System Stress Testing")
    print("Choose test scenario:")
    print("1. Quick stress test (100 users)")
    print("2. Medium stress test (500 users)")
    print("3. High stress test (1000 users)")
    print("4. Gradual load test (0-1000 users)")
    print("5. Custom test")
    
    choice = input("Enter choice (1-5): ").strip()
    
    base_url = input("Enter base URL (default: http://localhost): ").strip() or "http://localhost"
    
    stress_tester = CouponStressTest(base_url=base_url)
    
    try:
        if choice == "1":
            stress_tester.concurrent_users = 100
            await stress_tester.run_concurrent_test()
        elif choice == "2":
            stress_tester.concurrent_users = 500
            await stress_tester.run_concurrent_test()
        elif choice == "3":
            stress_tester.concurrent_users = 1000
            await stress_tester.run_concurrent_test()
        elif choice == "4":
            await stress_tester.run_gradual_load_test()
        elif choice == "5":
            users = int(input("Enter number of concurrent users: "))
            stock = int(input("Enter target stock (default: 1000): ") or "1000")
            stress_tester.concurrent_users = users
            await stress_tester.run_concurrent_test(target_stock=stock)
        else:
            print("Invalid choice. Running default test...")
            await stress_tester.run_concurrent_test()
            
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")

if __name__ == "__main__":
    # Example usage:
    # python stress_test.py
    asyncio.run(main())