"""
Kafka consumer service for processing coupon events and writing to MySQL
쿠폰 이벤트 처리 및 MySQL 작성을 위한 Kafka 컨슈머 서비스
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.messaging.kafka_client import KafkaEventConsumer
from app.database.connection import SessionLocal, create_tables
from app.database.models import CouponEvent, UserCoupon, CouponUsage, EventStats
import logging
import time
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CouponEventProcessor:
    """Process coupon events from Kafka and write to MySQL"""
    
    def __init__(self):
        self.consumer = KafkaEventConsumer("coupon-consumer-group")
        self.db = SessionLocal()
        
        # Ensure tables exist
        create_tables()
        logger.info("Consumer service initialized")
    
    def process_coupon_issued(self, event_data: Dict[str, Any]) -> bool:
        """Process coupon issued event"""
        try:
            user_coupon = UserCoupon(
                coupon_id=event_data['coupon_id'],
                user_id=event_data['user_id'],
                event_id=event_data['event_id'],
                issued_at=datetime.fromisoformat(event_data['issued_at']),
                is_used=False
            )
            
            self.db.add(user_coupon)
            self.db.commit()
            
            logger.info(f"Coupon issued record saved: {event_data['coupon_id']}")
            return True
            
        except IntegrityError as e:
            # Handle duplicate key errors (idempotency)
            self.db.rollback()
            if "Duplicate entry" in str(e):
                logger.warning(f"Duplicate coupon issuance ignored: {event_data['coupon_id']}")
                return True
            else:
                logger.error(f"Database integrity error: {e}")
                return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to process coupon_issued event: {e}")
            return False
    
    def process_coupon_redeemed(self, event_data: Dict[str, Any]) -> bool:
        """Process coupon redeemed event"""
        try:
            # Update user_coupon record
            user_coupon = self.db.query(UserCoupon).filter(
                UserCoupon.coupon_id == event_data['coupon_id']
            ).first()
            
            if user_coupon:
                user_coupon.is_used = True
                user_coupon.used_at = datetime.fromisoformat(event_data['redeemed_at'])
                
                # Create usage record
                coupon_usage = CouponUsage(
                    coupon_id=event_data['coupon_id'],
                    user_id=event_data['user_id'],
                    event_id=event_data['event_id'],
                    used_at=datetime.fromisoformat(event_data['redeemed_at'])
                )
                
                self.db.add(coupon_usage)
                self.db.commit()
                
                logger.info(f"Coupon redeemed record saved: {event_data['coupon_id']}")
                return True
            else:
                logger.warning(f"Coupon not found for redemption: {event_data['coupon_id']}")
                return False
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to process coupon_redeemed event: {e}")
            return False
    
    def process_stock_exhausted(self, event_data: Dict[str, Any]) -> bool:
        """Process stock exhausted event"""
        try:
            # Update event stock
            event = self.db.query(CouponEvent).filter(
                CouponEvent.event_id == event_data['event_id']
            ).first()
            
            if event:
                event.remaining_stock = event_data.get('remaining_stock', 0)
                event.is_active = False  # Deactivate event
                self.db.commit()
                
                logger.info(f"Event stock exhausted: {event_data['event_id']}")
                return True
            else:
                logger.warning(f"Event not found: {event_data['event_id']}")
                return False
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to process stock_exhausted event: {e}")
            return False
    
    def process_event(self, event: Dict[str, Any]) -> bool:
        """Process a single event based on its type"""
        event_type = event['value']['event_type']
        event_data = event['value']['data']
        
        if event_type == "coupon_issued":
            return self.process_coupon_issued(event_data)
        elif event_type == "coupon_redeemed":
            return self.process_coupon_redeemed(event_data)
        elif event_type == "stock_exhausted":
            return self.process_stock_exhausted(event_data)
        else:
            logger.warning(f"Unknown event type: {event_type}")
            return False
    
    def run(self):
        """Main consumer loop"""
        logger.info("Starting consumer loop...")
        
        try:
            while True:
                events = self.consumer.consume_events(timeout_ms=1000)
                
                if events:
                    logger.info(f"Processing {len(events)} events")
                    
                    success_count = 0
                    for event in events:
                        if self.process_event(event):
                            success_count += 1
                    
                    if success_count == len(events):
                        # All events processed successfully, commit offset
                        self.consumer.commit()
                        logger.info(f"Successfully processed {success_count} events")
                    else:
                        logger.error(f"Failed to process some events: {success_count}/{len(events)} successful")
                
                # Small delay to prevent CPU spinning
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Consumer loop error: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up resources...")
        try:
            self.consumer.close()
            self.db.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

def main():
    """Main entry point"""
    processor = CouponEventProcessor()
    processor.run()

if __name__ == "__main__":
    main()