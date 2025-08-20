"""
Redis Cluster connection and cache operations
Redis 클러스터 연결 및 캐시 연산
"""

import redis
from rediscluster import RedisCluster
import json
import os
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class RedisClusterClient:
    """Redis Cluster client for cache operations"""
    
    def __init__(self):
        # Redis Cluster startup nodes
        startup_nodes = [
            {"host": os.getenv("REDIS_HOST_1", "redis-node-1"), "port": int(os.getenv("REDIS_PORT_1", "7001"))},
            {"host": os.getenv("REDIS_HOST_2", "redis-node-2"), "port": int(os.getenv("REDIS_PORT_2", "7002"))},
            {"host": os.getenv("REDIS_HOST_3", "redis-node-3"), "port": int(os.getenv("REDIS_PORT_3", "7003"))},
        ]
        
        try:
            self.cluster = RedisCluster(
                startup_nodes=startup_nodes,
                decode_responses=True,
                skip_full_coverage_check=True,
                health_check_interval=30,
                socket_timeout=5,
                socket_connect_timeout=5,
                max_connections_per_node=50
            )
            logger.info("Redis Cluster connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis Cluster: {e}")
            # Fallback to single Redis for development
            self.cluster = redis.Redis(
                host=os.getenv("REDIS_HOST", "redis"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                decode_responses=True
            )
            logger.info("Fallback to single Redis instance")
    
    def load_lua_script(self, script_content: str) -> str:
        """Load Lua script and return SHA hash"""
        return self.cluster.script_load(script_content)
    
    def execute_lua_script(self, sha: str, keys: list, args: list):
        """Execute Lua script with SHA hash"""
        return self.cluster.evalsha(sha, len(keys), *keys, *args)

class CouponCache:
    """Cache operations for coupon system"""
    
    def __init__(self, redis_client: RedisClusterClient):
        self.redis = redis_client.cluster
        self.TTL_STOCK = 3600  # 1 hour
        self.TTL_USER_PARTICIPATION = 3600  # 1 hour
        self.TTL_EVENT_METADATA = 7200  # 2 hours
    
    # Stock management
    def get_stock_key(self, event_id: str) -> str:
        return f"coupon:stock:{event_id}"
    
    def get_participants_key(self, event_id: str) -> str:
        return f"coupon:participants:{event_id}"
    
    def get_user_coupon_key(self, user_id: str, event_id: str) -> str:
        return f"coupon:user:{user_id}:{event_id}"
    
    def initialize_stock(self, event_id: str, stock: int) -> bool:
        """Initialize stock in cache"""
        key = self.get_stock_key(event_id)
        return self.redis.set(key, stock, ex=self.TTL_STOCK, nx=True)
    
    def get_stock(self, event_id: str) -> Optional[int]:
        """Get current stock from cache"""
        key = self.get_stock_key(event_id)
        stock = self.redis.get(key)
        return int(stock) if stock else None
    
    def set_stock(self, event_id: str, stock: int) -> bool:
        """Set stock in cache"""
        key = self.get_stock_key(event_id)
        return self.redis.set(key, stock, ex=self.TTL_STOCK)
    
    def is_user_participated(self, event_id: str, user_id: str) -> bool:
        """Check if user already participated"""
        key = self.get_participants_key(event_id)
        return bool(self.redis.sismember(key, user_id))
    
    def add_participant(self, event_id: str, user_id: str) -> bool:
        """Add user to participants set"""
        key = self.get_participants_key(event_id)
        result = self.redis.sadd(key, user_id)
        self.redis.expire(key, self.TTL_USER_PARTICIPATION)
        return bool(result)
    
    def cache_user_coupon(self, user_id: str, event_id: str, coupon_id: str) -> bool:
        """Cache user's coupon"""
        key = self.get_user_coupon_key(user_id, event_id)
        return self.redis.set(key, coupon_id, ex=self.TTL_USER_PARTICIPATION)
    
    def get_user_coupon(self, user_id: str, event_id: str) -> Optional[str]:
        """Get user's coupon from cache"""
        key = self.get_user_coupon_key(user_id, event_id)
        return self.redis.get(key)
    
    def invalidate_event_cache(self, event_id: str):
        """Invalidate all cache related to an event"""
        keys_to_delete = [
            self.get_stock_key(event_id),
            self.get_participants_key(event_id)
        ]
        
        # Delete user coupon cache (this is approximate, in production use a proper pattern)
        for key in keys_to_delete:
            self.redis.delete(key)

# Global Redis Cluster client
redis_cluster_client = RedisClusterClient()
coupon_cache = CouponCache(redis_cluster_client)