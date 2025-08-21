"""
FastAPI application for coupon issuance system
쿠폰 발급 시스템을 위한 FastAPI 애플리케이션
"""

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import uuid
import os
from typing import Dict, Optional
from datetime import datetime
import logging

# Import our modules
from cache.redis_cluster import redis_cluster_client, coupon_cache
from messaging.kafka_client import get_kafka_producer
from database.connection import get_db, create_tables
from database.models import CouponEvent, UserCoupon
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Coupon System API",
    version="2.0.0",
    description="High-performance coupon issuance system with Redis Cluster and Kafka"
)

# Load Lua script for atomic operations
LUA_SCRIPT_PATH = "app/redis_scripts/coupon_issue_cluster.lua"
try:
    with open(LUA_SCRIPT_PATH, 'r') as f:
        COUPON_ISSUE_SCRIPT = f.read()
    
    # Register script with Redis Cluster
    coupon_issue_sha = redis_cluster_client.load_lua_script(COUPON_ISSUE_SCRIPT)
    logger.info("Lua script loaded successfully")
except Exception as e:
    logger.error(f"Failed to load Lua script: {e}")
    coupon_issue_sha = None

# Pydantic models
class CouponRequest(BaseModel):
    user_id: str
    event_id: str = "sample_event"

class CouponResponse(BaseModel):
    success: bool
    message: str
    coupon_id: Optional[str] = None
    remaining_stock: Optional[int] = None

class EventStatusResponse(BaseModel):
    event_id: str
    remaining_stock: int
    total_participants: int
    status: str

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database tables and cache"""
    try:
        create_tables()
        logger.info("Database tables created/verified")
        
        # Initialize sample event in cache
        coupon_cache.initialize_stock("sample_event", 1000)
        logger.info("Sample event initialized in cache")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint for load balancer"""
    return {
        "status": "healthy",
        "service": "coupon-api-v2",
        "timestamp": datetime.now().isoformat(),
        "redis_cluster": "connected",
        "kafka": "connected"
    }

@app.post("/api/v1/coupons/issue", response_model=CouponResponse)
async def issue_coupon(request: CouponRequest) -> CouponResponse:
    """
    Issue coupon using Redis Cluster atomic operations and Kafka events
    Redis 클러스터 원자적 연산과 Kafka 이벤트를 사용한 쿠폰 발급
    """
    if not coupon_issue_sha:
        raise HTTPException(status_code=500, detail="Lua script not available")
    
    try:
        # Initialize stock in cache if not exists
        if coupon_cache.get_stock(request.event_id) is None:
            coupon_cache.initialize_stock(request.event_id, 1000)
        
        # Generate unique coupon ID
        coupon_id = str(uuid.uuid4())
        
        # Prepare Redis keys
        stock_key = coupon_cache.get_stock_key(request.event_id)
        participants_key = coupon_cache.get_participants_key(request.event_id)
        
        # Execute atomic Lua script on Redis Cluster
        result = redis_cluster_client.execute_lua_script(
            coupon_issue_sha,
            [stock_key, participants_key],
            [request.user_id, coupon_id, 3600]  # 1 hour TTL
        )
        
        success_flag = result[0]
        message = result[1]
        
        if success_flag == 1:
            # Success - coupon issued atomically
            issued_coupon_id = result[2]
            remaining_stock = result[3]
            
            # Publish event to Kafka for persistence
            kafka_producer = get_kafka_producer()
            published = kafka_producer.publish_coupon_issued(
                request.user_id,
                request.event_id,
                issued_coupon_id
            )
            
            if not published:
                logger.warning(f"Failed to publish event for coupon: {issued_coupon_id}")
            
            # Check if stock is exhausted
            if remaining_stock <= 0:
                kafka_producer.publish_stock_exhausted(request.event_id, remaining_stock)
            
            return CouponResponse(
                success=True,
                message="Coupon issued successfully",
                coupon_id=issued_coupon_id,
                remaining_stock=remaining_stock
            )
        else:
            # Failed - return appropriate error
            error_messages = {
                'USER_ALREADY_PARTICIPATED': 'User already has a coupon for this event',
                'NO_STOCK_AVAILABLE': 'No coupons available',
                'STOCK_NOT_INITIALIZED': 'Event not found or not active'
            }
            
            return CouponResponse(
                success=False,
                message=error_messages.get(message, message),
                remaining_stock=coupon_cache.get_stock(request.event_id)
            )
        
    except Exception as e:
        logger.error(f"Coupon issuance error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/v1/coupons/status/{event_id}", response_model=EventStatusResponse)
async def get_coupon_status(event_id: str) -> EventStatusResponse:
    """Get current coupon status for an event from cache"""
    try:
        # Get data from cache (fast response)
        current_stock = coupon_cache.get_stock(event_id)
        participants_key = coupon_cache.get_participants_key(event_id)
        participant_count = redis_cluster_client.cluster.scard(participants_key)
        
        if current_stock is None:
            current_stock = 0
            
        return EventStatusResponse(
            event_id=event_id,
            remaining_stock=current_stock,
            total_participants=participant_count,
            status="active" if current_stock > 0 else "sold_out"
        )
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/v1/coupons/user/{user_id}/event/{event_id}")
async def get_user_coupon(user_id: str, event_id: str):
    """Get user's coupon for specific event"""
    try:
        # Check cache first
        cached_coupon = coupon_cache.get_user_coupon(user_id, event_id)
        if cached_coupon:
            return {
                "user_id": user_id,
                "event_id": event_id,
                "coupon_id": cached_coupon,
                "source": "cache"
            }
        
        return {
            "user_id": user_id,
            "event_id": event_id,
            "coupon_id": None,
            "message": "No coupon found"
        }
    except Exception as e:
        logger.error(f"User coupon lookup error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/v1/admin/events/{event_id}/stock")
async def initialize_event_stock(event_id: str, initial_stock: int):
    """Admin endpoint to initialize event stock"""
    try:
        success = coupon_cache.initialize_stock(event_id, initial_stock)
        if success:
            return {
                "event_id": event_id,
                "initial_stock": initial_stock,
                "message": "Stock initialized successfully"
            }
        else:
            return {
                "event_id": event_id,
                "message": "Stock already exists for this event"
            }
    except Exception as e:
        logger.error(f"Stock initialization error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/v1/admin/cache/stats")
async def get_cache_stats():
    """Admin endpoint for cache statistics"""
    try:
        # Get basic Redis Cluster info
        cluster_info = redis_cluster_client.cluster.info()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "redis_cluster_info": {
                "connected_slaves": cluster_info.get("connected_slaves", 0),
                "used_memory_human": cluster_info.get("used_memory_human", "unknown"),
                "total_commands_processed": cluster_info.get("total_commands_processed", 0)
            }
        }
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)