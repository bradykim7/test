import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const couponSuccessRate = new Rate('coupon_success_rate');
const couponResponseTime = new Trend('coupon_response_time');
const totalCouponsIssued = new Counter('total_coupons_issued');

// Extreme load test: 1M requests in 1 minute = ~16,667 RPS
export const options = {
    scenarios: {
        extreme_load: {
            executor: 'constant-arrival-rate',
            rate: 16667, // 16,667 requests per second = ~1M/minute
            timeUnit: '1s',
            duration: '1m',
            preAllocatedVUs: 1000,
            maxVUs: 5000, // Much higher VU limit for extreme load
            gracefulStop: '30s',
        }
    },
    thresholds: {
        'http_req_failed': ['rate<0.10'],     // Allow 10% failure rate under extreme load
        'http_req_duration': ['p(95)<2000'],  // 95% under 2 seconds (relaxed for extreme load)
        'coupon_success_rate': ['rate>=0.0005'], // At least 0.05% success rate (500 out of 1M)
    },
};

function generateUserId() {
    return `extreme_user_${__VU}_${__ITER}_${Math.random().toString(36).substr(2, 5)}`;
}

export default function () {
    const baseUrl = 'http://host.docker.internal';
    const payload = JSON.stringify({
        user_id: generateUserId(),
        event_id: 'extreme_load_test'
    });

    const headers = {
        'Content-Type': 'application/json',
    };

    const startTime = new Date().getTime();
    const response = http.post(`${baseUrl}/api/v1/coupons/issue`, payload, { headers });
    const endTime = new Date().getTime();
    
    const responseTime = endTime - startTime;
    couponResponseTime.add(responseTime);
    
    // Check response status
    const statusOk = check(response, {
        'status is 200 or 429': (r) => r.status === 200 || r.status === 429, // Accept rate limiting
        'response time < 5000ms': (r) => responseTime < 5000,
    });

    // Check if coupon was actually issued
    let couponIssued = false;
    if (response.status === 200) {
        try {
            const responseData = JSON.parse(response.body);
            couponIssued = responseData.success === true;
            if (couponIssued) {
                totalCouponsIssued.add(1);
            }
        } catch (e) {
            // Ignore parse errors under extreme load
        }
    }
    
    couponSuccessRate.add(couponIssued);
    
    // No sleep - maximum throughput
}

export function setup() {
    console.log('🚀 Starting EXTREME LOAD TEST: 1 Million requests in 1 minute');
    console.log('⚠️  This will generate ~16,667 RPS - ensure your system can handle it!');
    
    // Initialize test event with more stock for extreme test
    const baseUrl = 'http://host.docker.internal';
    const initResponse = http.post(`${baseUrl}/api/v1/admin/events/extreme_load_test/stock?initial_stock=10000`);
    
    console.log(`Setup: Event initialization returned status ${initResponse.status}`);
    
    if (initResponse.status !== 200) {
        console.log('❌ Setup failed - event initialization error');
        throw new Error('Event initialization failed');
    }
    
    return { startTime: new Date().getTime() };
}

export function teardown(data) {
    const endTime = new Date().getTime();
    const totalTestTime = (endTime - data.startTime) / 1000;
    
    console.log(`🏁 Extreme load test completed in ${totalTestTime.toFixed(2)} seconds`);
    
    // Check final event status
    const baseUrl = 'http://host.docker.internal';
    const statusResponse = http.get(`${baseUrl}/api/v1/coupons/status/extreme_load_test`);
    
    if (statusResponse.status === 200) {
        try {
            const status = JSON.parse(statusResponse.body);
            console.log(`📊 Final Results:`);
            console.log(`   - Remaining stock: ${status.remaining_stock}`);
            console.log(`   - Coupons issued: ${10000 - status.remaining_stock}`);
            console.log(`   - Stock depletion: ${((10000 - status.remaining_stock) / 10000 * 100).toFixed(2)}%`);
        } catch (e) {
            console.log('Could not parse final status');
        }
    }
}