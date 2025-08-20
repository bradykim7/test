-- MySQL initialization script for coupon system
-- 쿠폰 시스템을 위한 MySQL 초기화 스크립트

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS coupon_system;
USE coupon_system;

-- Create coupon_events table
CREATE TABLE IF NOT EXISTS coupon_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id VARCHAR(50) NOT NULL UNIQUE,
    event_name VARCHAR(200) NOT NULL,
    description TEXT,
    total_stock INT NOT NULL,
    remaining_stock INT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_event_id (event_id),
    INDEX idx_event_active_time (is_active, start_time, end_time)
);

-- Create user_coupons table
CREATE TABLE IF NOT EXISTS user_coupons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    coupon_id VARCHAR(36) NOT NULL UNIQUE,
    user_id VARCHAR(50) NOT NULL,
    event_id VARCHAR(50) NOT NULL,
    issued_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_used BOOLEAN DEFAULT FALSE,
    used_at DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE INDEX idx_user_event_unique (user_id, event_id),
    INDEX idx_coupon_lookup (coupon_id),
    INDEX idx_event_issued (event_id, issued_at),
    INDEX idx_user_coupons (user_id)
);

-- Create coupon_usage table
CREATE TABLE IF NOT EXISTS coupon_usage (
    id INT AUTO_INCREMENT PRIMARY KEY,
    coupon_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    event_id VARCHAR(50) NOT NULL,
    used_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    usage_context TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_usage_lookup (coupon_id, used_at),
    INDEX idx_user_usage (user_id),
    INDEX idx_event_usage (event_id, used_at)
);

-- Create event_stats table
CREATE TABLE IF NOT EXISTS event_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id VARCHAR(50) NOT NULL,
    stat_date DATETIME NOT NULL,
    total_requests INT DEFAULT 0,
    successful_issuances INT DEFAULT 0,
    failed_requests INT DEFAULT 0,
    stock_at_end INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE INDEX idx_stats_date (event_id, stat_date)
);

-- Insert sample event data
INSERT IGNORE INTO coupon_events (
    event_id, 
    event_name, 
    description, 
    total_stock, 
    remaining_stock, 
    start_time, 
    end_time
) VALUES (
    'sample_event', 
    'Sample Coupon Event', 
    'This is a sample coupon event for testing purposes', 
    1000, 
    1000, 
    NOW(), 
    DATE_ADD(NOW(), INTERVAL 7 DAY)
);

-- Grant permissions to coupon_user
GRANT ALL PRIVILEGES ON coupon_system.* TO 'coupon_user'@'%';
FLUSH PRIVILEGES;