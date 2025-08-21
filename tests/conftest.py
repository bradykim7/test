"""
Test configuration and fixtures for coupon system tests
쿠폰 시스템 테스트를 위한 테스트 구성 및 픽스처
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from main import app
from cache.redis_cluster import CouponCache
from messaging.kafka_client import KafkaProducer

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def client():
    """Create a test client for FastAPI app"""
    return TestClient(app)

@pytest.fixture
def mock_redis_cluster():
    """Mock Redis cluster client"""
    mock_cluster = MagicMock()
    mock_cluster.get.return_value = None
    mock_cluster.set.return_value = True
    mock_cluster.incr.return_value = 1
    mock_cluster.scard.return_value = 0
    mock_cluster.sadd.return_value = 1
    mock_cluster.sismember.return_value = False
    mock_cluster.expire.return_value = True
    mock_cluster.eval.return_value = [1, "SUCCESS", "test-coupon-id", 999]
    return mock_cluster

@pytest.fixture
def mock_coupon_cache(mock_redis_cluster):
    """Mock coupon cache with Redis cluster"""
    with patch('cache.redis_cluster.redis_cluster_client.cluster', mock_redis_cluster):
        cache = CouponCache()
        yield cache

@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer"""
    mock_producer = MagicMock(spec=KafkaProducer)
    mock_producer.publish_coupon_issued.return_value = True
    mock_producer.publish_stock_exhausted.return_value = True
    return mock_producer

@pytest.fixture
def sample_coupon_request():
    """Sample coupon request data"""
    return {
        "user_id": "test_user_123",
        "event_id": "test_event"
    }

@pytest.fixture
def sample_event_data():
    """Sample event data for testing"""
    return {
        "event_id": "test_event",
        "initial_stock": 1000,
        "current_stock": 500,
        "total_participants": 500
    }