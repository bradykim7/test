"""
Unit tests for Redis cache operations
Redis 캐시 작업을 위한 단위 테스트
"""

import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'app'))

from cache.redis_cluster import CouponCache

class TestCouponCache:
    """Test cases for CouponCache class"""

    def test_get_stock_key(self):
        """Test stock key generation"""
        cache = CouponCache()
        key = cache.get_stock_key("test_event")
        assert key == "coupon:test_event:stock"

    def test_get_participants_key(self):
        """Test participants key generation"""
        cache = CouponCache()
        key = cache.get_participants_key("test_event")
        assert key == "coupon:test_event:participants"

    @patch('cache.redis_cluster.redis_cluster_client.cluster')
    def test_initialize_stock_new_event(self, mock_cluster):
        """Test initializing stock for new event"""
        # Mock Redis responses
        mock_cluster.get.return_value = None  # Event doesn't exist
        mock_cluster.set.return_value = True
        mock_cluster.expire.return_value = True
        
        cache = CouponCache()
        result = cache.initialize_stock("new_event", 1000)
        
        assert result is True
        mock_cluster.set.assert_called_once_with("coupon:new_event:stock", 1000)
        mock_cluster.expire.assert_called_once_with("coupon:new_event:stock", 86400)

    @patch('cache.redis_cluster.redis_cluster_client.cluster')
    def test_initialize_stock_existing_event(self, mock_cluster):
        """Test initializing stock for existing event"""
        # Mock Redis responses
        mock_cluster.get.return_value = b'500'  # Event exists
        
        cache = CouponCache()
        result = cache.initialize_stock("existing_event", 1000)
        
        assert result is False
        mock_cluster.set.assert_not_called()

    @patch('cache.redis_cluster.redis_cluster_client.cluster')
    def test_get_stock_existing(self, mock_cluster):
        """Test getting stock for existing event"""
        mock_cluster.get.return_value = b'750'
        
        cache = CouponCache()
        stock = cache.get_stock("test_event")
        
        assert stock == 750
        mock_cluster.get.assert_called_once_with("coupon:test_event:stock")

    @patch('cache.redis_cluster.redis_cluster_client.cluster')
    def test_get_stock_non_existing(self, mock_cluster):
        """Test getting stock for non-existing event"""
        mock_cluster.get.return_value = None
        
        cache = CouponCache()
        stock = cache.get_stock("non_existing_event")
        
        assert stock is None

    @patch('cache.redis_cluster.redis_cluster_client.cluster')
    def test_check_user_participation_new_user(self, mock_cluster):
        """Test checking participation for new user"""
        mock_cluster.sismember.return_value = False
        
        cache = CouponCache()
        has_participated = cache.check_user_participation("new_user", "test_event")
        
        assert has_participated is False
        mock_cluster.sismember.assert_called_once_with(
            "coupon:test_event:participants", "new_user"
        )

    @patch('cache.redis_cluster.redis_cluster_client.cluster')
    def test_check_user_participation_existing_user(self, mock_cluster):
        """Test checking participation for existing user"""
        mock_cluster.sismember.return_value = True
        
        cache = CouponCache()
        has_participated = cache.check_user_participation("existing_user", "test_event")
        
        assert has_participated is True

    @patch('cache.redis_cluster.redis_cluster_client.cluster')
    def test_add_user_to_participants(self, mock_cluster):
        """Test adding user to participants set"""
        mock_cluster.sadd.return_value = 1
        
        cache = CouponCache()
        result = cache.add_user_to_participants("new_user", "test_event")
        
        assert result is True
        mock_cluster.sadd.assert_called_once_with(
            "coupon:test_event:participants", "new_user"
        )

    @patch('cache.redis_cluster.redis_cluster_client.cluster')
    def test_decrease_stock(self, mock_cluster):
        """Test decreasing stock"""
        mock_cluster.decr.return_value = 999
        
        cache = CouponCache()
        new_stock = cache.decrease_stock("test_event")
        
        assert new_stock == 999
        mock_cluster.decr.assert_called_once_with("coupon:test_event:stock")

    @patch('cache.redis_cluster.redis_cluster_client.cluster')
    def test_get_user_coupon_existing(self, mock_cluster):
        """Test getting user's coupon when it exists"""
        mock_cluster.get.return_value = b'coupon-id-123'
        
        cache = CouponCache()
        coupon_id = cache.get_user_coupon("user123", "test_event")
        
        assert coupon_id == "coupon-id-123"
        mock_cluster.get.assert_called_once_with("user_coupon:user123:test_event")

    @patch('cache.redis_cluster.redis_cluster_client.cluster')
    def test_get_user_coupon_non_existing(self, mock_cluster):
        """Test getting user's coupon when it doesn't exist"""
        mock_cluster.get.return_value = None
        
        cache = CouponCache()
        coupon_id = cache.get_user_coupon("user123", "test_event")
        
        assert coupon_id is None

    @patch('cache.redis_cluster.redis_cluster_client.cluster')
    def test_store_user_coupon(self, mock_cluster):
        """Test storing user's coupon"""
        mock_cluster.set.return_value = True
        mock_cluster.expire.return_value = True
        
        cache = CouponCache()
        result = cache.store_user_coupon("user123", "test_event", "coupon-id-123")
        
        assert result is True
        mock_cluster.set.assert_called_once_with(
            "user_coupon:user123:test_event", "coupon-id-123"
        )
        mock_cluster.expire.assert_called_once_with(
            "user_coupon:user123:test_event", 86400
        )