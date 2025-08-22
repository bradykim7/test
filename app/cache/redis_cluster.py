"""
Redis Cluster connection and cache operations
Redis 클러스터 연결 및 캐시 연산
"""

import redis
from redis.cluster import RedisCluster, ClusterNode
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class RedisClusterClient:
    """Redis Cluster client for cache operations"""
    
    def __init__(self):
        # Redis Cluster startup nodes - use dict format for redis-py 5.0+
        nodes_info = [
            {"host": os.getenv("REDIS_HOST_1", "redis-node-1"), "port": int(os.getenv("REDIS_PORT_1", "7001"))},
            {"host": os.getenv("REDIS_HOST_2", "redis-node-2"), "port": int(os.getenv("REDIS_PORT_2", "7002"))},
            {"host": os.getenv("REDIS_HOST_3", "redis-node-3"), "port": int(os.getenv("REDIS_PORT_3", "7003"))},
        ]
        startup_nodes = [ClusterNode(node['host'], node['port']) for node in nodes_info]

        try:
            self.cluster = RedisCluster(
                startup_nodes=startup_nodes,
                decode_responses=True,
                skip_full_coverage_check=True,
                health_check_interval=30,
                socket_timeout=10,
                socket_connect_timeout=10,
                retry_on_timeout=True,
                max_connections=50
            )
            logger.info("Redis Cluster connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis Cluster: {e}")
            raise e
    
    def load_lua_script(self, script_content: str) -> str:
        """Load Lua script and return SHA hash"""
        return self.cluster.script_load(script_content)
    
    def execute_lua_script(self, sha: str, keys: list, args: list) -> any:
        """Execute Lua script with SHA hash"""
        return self.cluster.evalsha(sha, len(keys), *keys, *args)

class CouponCache:
    """Cache operations for coupon system"""
    
    def __init__(self, redis_client: RedisClusterClient):
        self.redis = redis_client.cluster
        self.TTL_STOCK = 3600  # 1 hour
        self.TTL_USER_PARTICIPATION = 3600  # 1 hour
    
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
        try:
            key = self.get_stock_key(event_id)
            stock = self.redis.get(key)
            return int(stock) if stock else None
        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing stock value for event {event_id}: {e}")
            return None
    
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
        # Only set TTL if this is a new set (result > 0 means user was added)
        if result > 0:
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
        try:
            # Find user coupon keys using pattern matching
            user_coupon_pattern = f"coupon:user:*:{event_id}"
            user_keys = self.redis.keys(user_coupon_pattern)
            
            keys_to_delete = [
                self.get_stock_key(event_id),
                self.get_participants_key(event_id)
            ] + user_keys
            
            # Delete all keys if any exist
            if keys_to_delete:
                self.redis.delete(*keys_to_delete)
                logger.info(f"Invalidated {len(keys_to_delete)} cache keys for event {event_id}")
        except Exception as e:
            logger.error(f"Error invalidating cache for event {event_id}: {e}")

# Global Redis Cluster client - use lazy initialization
redis_cluster_client = None
coupon_cache = None

def get_redis_cluster_client():
    """Get Redis cluster client with lazy initialization"""
    global redis_cluster_client
    if redis_cluster_client is None:
        redis_cluster_client = RedisClusterClient()
    return redis_cluster_client

def get_coupon_cache():
    """Get coupon cache with lazy initialization"""
    global coupon_cache
    if coupon_cache is None:
        coupon_cache = CouponCache(get_redis_cluster_client())
    return coupon_cache
