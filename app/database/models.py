"""
MySQL database models for persistent storage
영구 저장을 위한 MySQL 데이터베이스 모델
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

class CouponEvent(Base):
    """
    Coupon event master table
    쿠폰 이벤트 마스터 테이블
    """
    __tablename__ = "coupon_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(50), unique=True, nullable=False, index=True)
    event_name = Column(String(200), nullable=False)
    description = Column(Text)
    total_stock = Column(Integer, nullable=False)
    remaining_stock = Column(Integer, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Index for performance
    __table_args__ = (
        Index('idx_event_active_time', 'is_active', 'start_time', 'end_time'),
    )

class UserCoupon(Base):
    """
    User coupon issuance records
    사용자 쿠폰 발급 기록
    """
    __tablename__ = "user_coupons"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    coupon_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    user_id = Column(String(50), nullable=False, index=True)
    event_id = Column(String(50), nullable=False, index=True)
    issued_at = Column(DateTime, server_default=func.now())
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # Composite unique index to prevent duplicate issuance
    __table_args__ = (
        Index('idx_user_event_unique', 'user_id', 'event_id', unique=True),
        Index('idx_coupon_lookup', 'coupon_id'),
        Index('idx_event_issued', 'event_id', 'issued_at'),
    )

class CouponUsage(Base):
    """
    Coupon usage/redemption records
    쿠폰 사용/상환 기록
    """
    __tablename__ = "coupon_usage"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    coupon_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    event_id = Column(String(50), nullable=False, index=True)
    used_at = Column(DateTime, server_default=func.now())
    usage_context = Column(Text)  # Additional context about usage
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_usage_lookup', 'coupon_id', 'used_at'),
    )

class EventStats(Base):
    """
    Event statistics for monitoring and analytics
    모니터링 및 분석을 위한 이벤트 통계
    """
    __tablename__ = "event_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(50), nullable=False, index=True)
    stat_date = Column(DateTime, nullable=False)
    total_requests = Column(Integer, default=0)
    successful_issuances = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    stock_at_end = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_stats_date', 'event_id', 'stat_date', unique=True),
    )