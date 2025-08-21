"""
Integration tests for FastAPI endpoints
FastAPI 엔드포인트를 위한 통합 테스트
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'app'))

from main import app

class TestCouponAPI:
    """Integration tests for coupon API endpoints"""

    def test_health_check(self):
        """Test health check endpoint"""
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "coupon-api-v2"
        assert "timestamp" in data

    @patch('main.redis_cluster_client')
    @patch('main.get_kafka_producer')
    @patch('main.coupon_issue_sha', 'mock_sha')
    def test_issue_coupon_success(self, mock_get_kafka_producer, mock_redis_client):
        """Test successful coupon issuance"""
        # Mock Redis responses
        mock_redis_client.execute_lua_script.return_value = [1, "SUCCESS", "coupon-123", 999]
        
        # Mock Kafka producer
        mock_producer = MagicMock()
        mock_producer.publish_coupon_issued.return_value = True
        mock_get_kafka_producer.return_value = mock_producer
        
        # Mock cache operations
        with patch('main.coupon_cache') as mock_cache:
            mock_cache.get_stock.return_value = 1000
            mock_cache.initialize_stock.return_value = True
            mock_cache.get_stock_key.return_value = "coupon:test_event:stock"
            mock_cache.get_participants_key.return_value = "coupon:test_event:participants"
            
            client = TestClient(app)
            response = client.post(
                "/api/v1/coupons/issue",
                json={"user_id": "user123", "event_id": "test_event"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "Coupon issued successfully"
            assert data["coupon_id"] == "coupon-123"
            assert data["remaining_stock"] == 999

    @patch('main.redis_cluster_client')
    @patch('main.get_kafka_producer')
    @patch('main.coupon_issue_sha', 'mock_sha')
    def test_issue_coupon_user_already_participated(self, mock_get_kafka_producer, mock_redis_client):
        """Test coupon issuance when user already participated"""
        # Mock Redis responses for already participated user
        mock_redis_client.execute_lua_script.return_value = [0, "USER_ALREADY_PARTICIPATED"]
        
        # Mock cache operations
        with patch('main.coupon_cache') as mock_cache:
            mock_cache.get_stock.return_value = 500
            mock_cache.initialize_stock.return_value = True
            mock_cache.get_stock_key.return_value = "coupon:test_event:stock"
            mock_cache.get_participants_key.return_value = "coupon:test_event:participants"
            
            client = TestClient(app)
            response = client.post(
                "/api/v1/coupons/issue",
                json={"user_id": "user123", "event_id": "test_event"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert data["message"] == "User already has a coupon for this event"
            assert data["remaining_stock"] == 500

    @patch('main.redis_cluster_client')
    @patch('main.get_kafka_producer')
    @patch('main.coupon_issue_sha', 'mock_sha')
    def test_issue_coupon_no_stock(self, mock_get_kafka_producer, mock_redis_client):
        """Test coupon issuance when no stock available"""
        # Mock Redis responses for no stock
        mock_redis_client.execute_lua_script.return_value = [0, "NO_STOCK_AVAILABLE"]
        
        # Mock cache operations
        with patch('main.coupon_cache') as mock_cache:
            mock_cache.get_stock.return_value = 0
            mock_cache.initialize_stock.return_value = True
            mock_cache.get_stock_key.return_value = "coupon:test_event:stock"
            mock_cache.get_participants_key.return_value = "coupon:test_event:participants"
            
            client = TestClient(app)
            response = client.post(
                "/api/v1/coupons/issue",
                json={"user_id": "user123", "event_id": "test_event"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert data["message"] == "No coupons available"
            assert data["remaining_stock"] == 0

    @patch('main.coupon_issue_sha', None)
    def test_issue_coupon_lua_script_not_available(self):
        """Test coupon issuance when Lua script is not available"""
        client = TestClient(app)
        response = client.post(
            "/api/v1/coupons/issue",
            json={"user_id": "user123", "event_id": "test_event"}
        )
        
        assert response.status_code == 500
        data = response.json()
        assert "Lua script not available" in data["detail"]

    def test_issue_coupon_invalid_request(self):
        """Test coupon issuance with invalid request data"""
        client = TestClient(app)
        response = client.post(
            "/api/v1/coupons/issue",
            json={"user_id": ""}  # Missing event_id and empty user_id
        )
        
        assert response.status_code == 422  # Validation error

    @patch('main.redis_cluster_client')
    def test_get_coupon_status(self, mock_redis_client):
        """Test getting coupon status for an event"""
        # Mock cache operations
        with patch('main.coupon_cache') as mock_cache:
            mock_cache.get_stock.return_value = 750
            mock_cache.get_participants_key.return_value = "coupon:test_event:participants"
            
            # Mock Redis cluster responses
            mock_redis_client.cluster.scard.return_value = 250
            
            client = TestClient(app)
            response = client.get("/api/v1/coupons/status/test_event")
            
            assert response.status_code == 200
            data = response.json()
            assert data["event_id"] == "test_event"
            assert data["remaining_stock"] == 750
            assert data["total_participants"] == 250
            assert data["status"] == "active"

    @patch('main.redis_cluster_client')
    def test_get_coupon_status_sold_out(self, mock_redis_client):
        """Test getting coupon status for sold out event"""
        # Mock cache operations
        with patch('main.coupon_cache') as mock_cache:
            mock_cache.get_stock.return_value = 0
            mock_cache.get_participants_key.return_value = "coupon:test_event:participants"
            
            # Mock Redis cluster responses
            mock_redis_client.cluster.scard.return_value = 1000
            
            client = TestClient(app)
            response = client.get("/api/v1/coupons/status/test_event")
            
            assert response.status_code == 200
            data = response.json()
            assert data["event_id"] == "test_event"
            assert data["remaining_stock"] == 0
            assert data["total_participants"] == 1000
            assert data["status"] == "sold_out"

    def test_get_user_coupon_found(self):
        """Test getting user's coupon when it exists"""
        with patch('main.coupon_cache') as mock_cache:
            mock_cache.get_user_coupon.return_value = "coupon-123"
            
            client = TestClient(app)
            response = client.get("/api/v1/coupons/user/user123/event/test_event")
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "user123"
            assert data["event_id"] == "test_event"
            assert data["coupon_id"] == "coupon-123"
            assert data["source"] == "cache"

    def test_get_user_coupon_not_found(self):
        """Test getting user's coupon when it doesn't exist"""
        with patch('main.coupon_cache') as mock_cache:
            mock_cache.get_user_coupon.return_value = None
            
            client = TestClient(app)
            response = client.get("/api/v1/coupons/user/user123/event/test_event")
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "user123"
            assert data["event_id"] == "test_event"
            assert data["coupon_id"] is None
            assert data["message"] == "No coupon found"

    def test_initialize_event_stock_success(self):
        """Test successful event stock initialization"""
        with patch('main.coupon_cache') as mock_cache:
            mock_cache.initialize_stock.return_value = True
            
            client = TestClient(app)
            response = client.post("/api/v1/admin/events/new_event/stock?initial_stock=2000")
            
            assert response.status_code == 200
            data = response.json()
            assert data["event_id"] == "new_event"
            assert data["initial_stock"] == 2000
            assert data["message"] == "Stock initialized successfully"

    def test_initialize_event_stock_already_exists(self):
        """Test event stock initialization when stock already exists"""
        with patch('main.coupon_cache') as mock_cache:
            mock_cache.initialize_stock.return_value = False
            
            client = TestClient(app)
            response = client.post("/api/v1/admin/events/existing_event/stock?initial_stock=2000")
            
            assert response.status_code == 200
            data = response.json()
            assert data["event_id"] == "existing_event"
            assert data["message"] == "Stock already exists for this event"

    @patch('main.redis_cluster_client')
    def test_get_cache_stats(self, mock_redis_client):
        """Test getting cache statistics"""
        # Mock Redis cluster info
        mock_redis_client.cluster.info.return_value = {
            "connected_slaves": 3,
            "used_memory_human": "10.5M",
            "total_commands_processed": 1000000
        }
        
        client = TestClient(app)
        response = client.get("/api/v1/admin/cache/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert data["redis_cluster_info"]["connected_slaves"] == 3
        assert data["redis_cluster_info"]["used_memory_human"] == "10.5M"
        assert data["redis_cluster_info"]["total_commands_processed"] == 1000000