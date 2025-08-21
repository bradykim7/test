-- Atomic coupon issuance Lua script for Redis Cluster
-- Redis 클러스터용 원자적 쿠폰 발급 Lua 스크립트

-- KEYS[1]: coupon:stock:event_id (coupon stock key)
-- KEYS[2]: coupon:participants:event_id (set of participants)
-- KEYS[3]: coupon:user:{event_id}:user_id (user's coupon cache key)
-- ARGV[1]: user_id
-- ARGV[2]: coupon_id (UUID)
-- ARGV[3]: expiry_time (seconds for cache TTL)

local stock_key = KEYS[1]
local participants_key = KEYS[2]
local user_coupon_key = KEYS[3] -- Get user coupon key from KEYS array

local user_id = ARGV[1]
local coupon_id = ARGV[2]
local expiry_time = tonumber(ARGV[3])

-- Check if user already participated
-- 사용자가 이미 참여했는지 확인
if redis.call('SISMEMBER', participants_key, user_id) == 1 then
    return {0, 'USER_ALREADY_PARTICIPATED'}
end

-- Get current stock
-- 현재 재고 확인
local current_stock = redis.call('GET', stock_key)
if not current_stock then
    return {0, 'STOCK_NOT_INITIALIZED'}
end

current_stock = tonumber(current_stock)

-- Check if stock is available
-- 재고가 있는지 확인
if current_stock <= 0 then
    return {0, 'NO_STOCK_AVAILABLE'}
end

-- Atomic operations: decrement stock and add user to participants
-- 원자적 연산: 재고 감소 및 사용자를 참여자에 추가
redis.call('SADD', participants_key, user_id)

-- DECR returns the value AFTER decrementing.
-- DECR은 감소 후의 값을 반환합니다.
local remaining_stock = redis.call('DECR', stock_key)

-- Set TTL for participants set to prevent memory leaks
-- 메모리 누수 방지를 위해 참여자 집합에 TTL 설정
redis.call('EXPIRE', participants_key, expiry_time)

-- Cache user's coupon with TTL
-- TTL과 함께 사용자 쿠폰 캐시
redis.call('SETEX', user_coupon_key, expiry_time, coupon_id)

-- Return success with remaining stock
-- 남은 재고와 함께 성공 반환
return {1, 'SUCCESS', coupon_id, tonumber(remaining_stock)}