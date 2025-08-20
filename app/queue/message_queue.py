"""
Simple message queue implementation using Redis
Redis를 사용한 간단한 메시지 큐 구현
"""

import json
import redis
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

class SimpleMessageQueue:
    """Simple Redis-based message queue for coupon events"""
    
    def __init__(self, redis_client: redis.Redis, queue_name: str = "coupon_events"):
        self.redis = redis_client
        self.queue_name = queue_name
        self.processing_queue = f"{queue_name}:processing"
        self.dead_letter_queue = f"{queue_name}:dlq"
    
    def publish(self, event_type: str, data: Dict[str, Any]) -> str:
        """
        Publish an event to the queue
        큐에 이벤트 발행
        """
        message_id = str(uuid.uuid4())
        message = {
            "id": message_id,
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "retry_count": 0
        }
        
        # Push to the main queue
        self.redis.lpush(self.queue_name, json.dumps(message))
        return message_id
    
    def consume(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """
        Consume a message from the queue (blocking)
        큐에서 메시지 소비 (블로킹)
        """
        # Move message from main queue to processing queue atomically
        result = self.redis.brpoplpush(
            self.queue_name, 
            self.processing_queue, 
            timeout
        )
        
        if result:
            return json.loads(result)
        return None
    
    def acknowledge(self, message_id: str) -> bool:
        """
        Acknowledge successful processing of a message
        메시지 처리 성공 확인
        """
        # Remove from processing queue
        messages = self.redis.lrange(self.processing_queue, 0, -1)
        for msg_json in messages:
            msg = json.loads(msg_json)
            if msg["id"] == message_id:
                self.redis.lrem(self.processing_queue, 1, msg_json)
                return True
        return False
    
    def reject(self, message_id: str, max_retries: int = 3) -> bool:
        """
        Reject a message and potentially retry or send to DLQ
        메시지 거부 및 재시도 또는 DLQ 전송
        """
        messages = self.redis.lrange(self.processing_queue, 0, -1)
        for msg_json in messages:
            msg = json.loads(msg_json)
            if msg["id"] == message_id:
                # Remove from processing queue
                self.redis.lrem(self.processing_queue, 1, msg_json)
                
                # Increment retry count
                msg["retry_count"] += 1
                
                if msg["retry_count"] < max_retries:
                    # Retry - put back to main queue
                    self.redis.lpush(self.queue_name, json.dumps(msg))
                else:
                    # Send to dead letter queue
                    msg["failed_at"] = datetime.now().isoformat()
                    self.redis.lpush(self.dead_letter_queue, json.dumps(msg))
                
                return True
        return False
    
    def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        return {
            "pending": self.redis.llen(self.queue_name),
            "processing": self.redis.llen(self.processing_queue),
            "dead_letter": self.redis.llen(self.dead_letter_queue)
        }

class CouponEventPublisher:
    """Publisher for coupon-related events"""
    
    def __init__(self, message_queue: SimpleMessageQueue):
        self.queue = message_queue
    
    def publish_coupon_issued(self, user_id: str, event_id: str, coupon_id: str) -> str:
        """Publish coupon issued event"""
        return self.queue.publish("coupon_issued", {
            "user_id": user_id,
            "event_id": event_id,
            "coupon_id": coupon_id,
            "issued_at": datetime.now().isoformat()
        })
    
    def publish_coupon_redeemed(self, user_id: str, event_id: str, coupon_id: str) -> str:
        """Publish coupon redeemed event"""
        return self.queue.publish("coupon_redeemed", {
            "user_id": user_id,
            "event_id": event_id,
            "coupon_id": coupon_id,
            "redeemed_at": datetime.now().isoformat()
        })
    
    def publish_stock_exhausted(self, event_id: str) -> str:
        """Publish stock exhausted event"""
        return self.queue.publish("stock_exhausted", {
            "event_id": event_id,
            "exhausted_at": datetime.now().isoformat()
        })