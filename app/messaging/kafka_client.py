"""
Kafka client for event streaming
이벤트 스트리밍을 위한 Kafka 클라이언트
"""

from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import json
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class KafkaEventProducer:
    """Kafka producer for coupon events"""
    
    def __init__(self):
        self.bootstrap_servers = [
            f"{os.getenv('KAFKA_HOST_1', 'kafka-1')}:{os.getenv('KAFKA_PORT_1', '9092')}",
            f"{os.getenv('KAFKA_HOST_2', 'kafka-2')}:{os.getenv('KAFKA_PORT_2', '9092')}",
            f"{os.getenv('KAFKA_HOST_3', 'kafka-3')}:{os.getenv('KAFKA_PORT_3', '9092')}"
        ]
        
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas
                retries=3,
                max_in_flight_requests_per_connection=1,  # Ensure ordering
                enable_idempotence=True,  # Exactly once semantics
                batch_size=16384,
                linger_ms=10,
                compression_type='snappy'
            )
            logger.info("Kafka producer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise
    
    def _create_event_message(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create standardized event message"""
        return {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "version": "1.0",
            "data": data
        }
    
    def publish_coupon_issued(self, user_id: str, event_id: str, coupon_id: str) -> bool:
        """Publish coupon issued event"""
        try:
            message = self._create_event_message("coupon_issued", {
                "user_id": user_id,
                "event_id": event_id,
                "coupon_id": coupon_id,
                "issued_at": datetime.now().isoformat()
            })
            
            # Use event_id as partition key for consistent partitioning
            future = self.producer.send(
                topic="coupon-events",
                key=event_id,
                value=message
            )
            
            # Wait for the result (synchronous for reliability)
            record_metadata = future.get(timeout=10)
            logger.info(f"Message sent to topic {record_metadata.topic} partition {record_metadata.partition}")
            return True
            
        except KafkaError as e:
            logger.error(f"Failed to publish coupon_issued event: {e}")
            return False
    
    def publish_coupon_redeemed(self, user_id: str, event_id: str, coupon_id: str) -> bool:
        """Publish coupon redeemed event"""
        try:
            message = self._create_event_message("coupon_redeemed", {
                "user_id": user_id,
                "event_id": event_id,
                "coupon_id": coupon_id,
                "redeemed_at": datetime.now().isoformat()
            })
            
            future = self.producer.send(
                topic="coupon-events",
                key=event_id,
                value=message
            )
            
            future.get(timeout=10)
            return True
            
        except KafkaError as e:
            logger.error(f"Failed to publish coupon_redeemed event: {e}")
            return False
    
    def publish_stock_exhausted(self, event_id: str, remaining_stock: int = 0) -> bool:
        """Publish stock exhausted event"""
        try:
            message = self._create_event_message("stock_exhausted", {
                "event_id": event_id,
                "remaining_stock": remaining_stock,
                "exhausted_at": datetime.now().isoformat()
            })
            
            future = self.producer.send(
                topic="coupon-events",
                key=event_id,
                value=message
            )
            
            future.get(timeout=10)
            return True
            
        except KafkaError as e:
            logger.error(f"Failed to publish stock_exhausted event: {e}")
            return False
    
    def close(self):
        """Close the producer"""
        if self.producer:
            self.producer.close()

class KafkaEventConsumer:
    """Kafka consumer for processing coupon events"""
    
    def __init__(self, consumer_group: str = "coupon-consumer-group"):
        self.bootstrap_servers = [
            f"{os.getenv('KAFKA_HOST_1', 'kafka-1')}:{os.getenv('KAFKA_PORT_1', '9092')}",
            f"{os.getenv('KAFKA_HOST_2', 'kafka-2')}:{os.getenv('KAFKA_PORT_2', '9092')}",
            f"{os.getenv('KAFKA_HOST_3', 'kafka-3')}:{os.getenv('KAFKA_PORT_3', '9092')}"
        ]
        self.consumer_group = consumer_group
        
        try:
            self.consumer = KafkaConsumer(
                'coupon-events',
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.consumer_group,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                enable_auto_commit=False,  # Manual commit for reliability
                auto_offset_reset='earliest',
                max_poll_records=100,
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000
            )
            logger.info(f"Kafka consumer initialized for group: {consumer_group}")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}")
            raise
    
    def consume_events(self, timeout_ms: int = 1000) -> List[Dict[str, Any]]:
        """Consume events from Kafka"""
        try:
            message_pack = self.consumer.poll(timeout_ms=timeout_ms)
            events = []
            
            for topic_partition, messages in message_pack.items():
                for message in messages:
                    events.append({
                        'topic': message.topic,
                        'partition': message.partition,
                        'offset': message.offset,
                        'key': message.key,
                        'value': message.value,
                        'timestamp': message.timestamp
                    })
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to consume events: {e}")
            return []
    
    def commit(self):
        """Manually commit offsets"""
        try:
            self.consumer.commit()
        except Exception as e:
            logger.error(f"Failed to commit offsets: {e}")
    
    def close(self):
        """Close the consumer"""
        if self.consumer:
            self.consumer.close()

# Global Kafka producer instance
kafka_producer = None

def get_kafka_producer() -> KafkaEventProducer:
    """Get global Kafka producer instance"""
    global kafka_producer
    if kafka_producer is None:
        kafka_producer = KafkaEventProducer()
    return kafka_producer