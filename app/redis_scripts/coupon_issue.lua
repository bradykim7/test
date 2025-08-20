-- Atomic coupon issuance Lua script for Redis
-- 원자적 쿠폰 발급을 위한 Redis Lua 스크립트

-- KEYS[1]: coupon:event_id:stock (coupon stock key)
-- KEYS[2]: coupon:event_id:participants (set of participants)
-- ARGV[1]: user_id
-- ARGV[2]: coupon_id (UUID)
-- ARGV[3]: expiry_time (seconds)

local stock_key = KEYS[1]
local participants_key = KEYS[2]
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
    -- Initialize stock if not exists (for demo purposes)
    -- 재고가 없으면 초기화 (데모용)
    redis.call('SET', stock_key, 1000)
    current_stock = 1000
else
    current_stock = tonumber(current_stock)
end

-- Check if stock is available
-- 재고가 있는지 확인
if current_stock <= 0 then
    return {0, 'NO_STOCK_AVAILABLE'}
end

-- Atomic operations: decrement stock and add user to participants
-- 원자적 연산: 재고 감소 및 사용자를 참여자에 추가
redis.call('DECR', stock_key)
redis.call('SADD', participants_key, user_id)

-- Store user's coupon with expiry
-- 만료 시간과 함께 사용자 쿠폰 저장
local user_coupon_key = 'coupon:user:' .. user_id .. ':' .. string.match(stock_key, ':([^:]+):')
redis.call('SETEX', user_coupon_key, expiry_time, coupon_id)

-- Return success with remaining stock
-- 남은 재고와 함께 성공 반환
local remaining_stock = redis.call('GET', stock_key)
return {1, 'SUCCESS', coupon_id, tonumber(remaining_stock)}