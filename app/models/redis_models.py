"""
Redis data models for coupon system
쿠폰 시스템을 위한 Redis 데이터 모델
"""

from typing import Optional, Set
import redis
import json
from datetime import datetime, timedelta

class RedisDataModel:
    """Base class for Redis data models"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

class CouponStock(RedisDataModel):
    """
    Manages coupon stock for events
    이벤트의 쿠폰 재고 관리
    
    Key pattern: coupon:{event_id}:stock
    """
    
    def get_key(self, event_id: str) -> str:
        return f"coupon:{event_id}:stock"
    
    def initialize_stock(self, event_id: str, initial_stock: int) -> bool:
        """Initialize stock for an event"""
        key = self.get_key(event_id)
        return self.redis.set(key, initial_stock, nx=True)  # Only set if not exists
    
    def get_stock(self, event_id: str) -> Optional[int]:
        """Get current stock for an event"""
        key = self.get_key(event_id)
        stock = self.redis.get(key)
        return int(stock) if stock else None
    
    def set_stock(self, event_id: str, stock: int) -> bool:
        """Set stock for an event"""
        key = self.get_key(event_id)
        return self.redis.set(key, stock)

class CouponParticipants(RedisDataModel):
    """
    Manages participants for coupon events
    쿠폰 이벤트 참여자 관리
    
    Key pattern: coupon:{event_id}:participants
    """
    
    def get_key(self, event_id: str) -> str:
        return f"coupon:{event_id}:participants"
    
    def add_participant(self, event_id: str, user_id: str) -> bool:
        """Add a participant to an event"""
        key = self.get_key(event_id)
        return bool(self.redis.sadd(key, user_id))
    
    def is_participant(self, event_id: str, user_id: str) -> bool:
        """Check if user is already a participant"""
        key = self.get_key(event_id)
        return bool(self.redis.sismember(key, user_id))
    
    def get_participant_count(self, event_id: str) -> int:
        """Get total number of participants"""
        key = self.get_key(event_id)
        return self.redis.scard(key)
    
    def get_participants(self, event_id: str) -> Set[str]:
        """Get all participants for an event"""
        key = self.get_key(event_id)
        return self.redis.smembers(key)

class UserCoupon(RedisDataModel):
    """
    Manages individual user coupons
    개별 사용자 쿠폰 관리
    
    Key pattern: coupon:user:{user_id}:{event_id}
    """
    
    def get_key(self, user_id: str, event_id: str) -> str:
        return f"coupon:user:{user_id}:{event_id}"
    
    def store_coupon(self, user_id: str, event_id: str, coupon_id: str, expiry_hours: int = 24) -> bool:
        """Store a coupon for a user with expiry"""
        key = self.get_key(user_id, event_id)
        expiry_seconds = expiry_hours * 3600
        return self.redis.setex(key, expiry_seconds, coupon_id)
    
    def get_coupon(self, user_id: str, event_id: str) -> Optional[str]:
        """Get user's coupon for an event"""
        key = self.get_key(user_id, event_id)
        return self.redis.get(key)
    
    def has_coupon(self, user_id: str, event_id: str) -> bool:
        """Check if user has a coupon for an event"""
        key = self.get_key(user_id, event_id)
        return bool(self.redis.exists(key))

class EventMetadata(RedisDataModel):
    """
    Manages event metadata
    이벤트 메타데이터 관리
    
    Key pattern: coupon:event:{event_id}:meta
    """
    
    def get_key(self, event_id: str) -> str:
        return f"coupon:event:{event_id}:meta"
    
    def create_event(self, event_id: str, initial_stock: int, 
                    start_time: datetime, end_time: datetime, 
                    description: str = "") -> bool:
        """Create a new coupon event"""
        metadata = {
            "event_id": event_id,
            "initial_stock": initial_stock,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "description": description,
            "created_at": datetime.now().isoformat()
        }
        
        key = self.get_key(event_id)
        return self.redis.set(key, json.dumps(metadata), nx=True)
    
    def get_event(self, event_id: str) -> Optional[dict]:
        """Get event metadata"""
        key = self.get_key(event_id)
        data = self.redis.get(key)
        return json.loads(data) if data else None
    
    def is_event_active(self, event_id: str) -> bool:
        """Check if event is currently active"""
        event = self.get_event(event_id)
        if not event:
            return False
        
        now = datetime.now()
        start_time = datetime.fromisoformat(event["start_time"])
        end_time = datetime.fromisoformat(event["end_time"])
        
        return start_time <= now <= end_time