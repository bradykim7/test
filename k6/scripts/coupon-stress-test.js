import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const couponSuccessRate = new Rate('coupon_success_rate');
const couponResponseTime = new Trend('coupon_response_time');

// Test configuration
export const options = {
    scenarios: {
        // Stress test scenario: 1M users competing for 1K coupons
        stress_test: {
            executor: 'constant-arrival-rate',
            rate: 1000, // 1000 requests per second
            timeUnit: '1s',
            duration: '2m',
            preAllocatedVUs: 100,
            maxVUs: 1000,
            gracefulStop: '30s',
        }
    },
    thresholds: {
        'http_req_failed': ['rate<0.05'],   // HTTP error rate < 5%
        'http_req_duration': ['p(95)<1000'], // 95% of requests < 1s
        'coupon_success_rate': ['rate>=0.001'], // At least 0.1% success rate (1K out of 100K+ requests)
    },
};

// Generate unique user ID for each virtual user
function generateUserId() {
    return `k6_user_${__VU}_${__ITER}_${Math.random().toString(36).substr(2, 9)}`;
}

export default function () {
    const baseUrl = 'http://host.docker.internal'; // Access host from container
    const payload = JSON.stringify({
        user_id: generateUserId(),
        event_id: 'k6_stress_test'
    });

    const headers = {
        'Content-Type': 'application/json',
    };

    // Issue coupon request
    const response = http.post(`${baseUrl}/api/v1/coupons/issue`, payload, { headers });
    
    // Record response time
    couponResponseTime.add(response.timings.duration);
    
    // Check response
    const isSuccess = check(response, {
        'status is 200': (r) => r.status === 200,
        'response time < 1000ms': (r) => r.timings.duration < 1000,
    });

    // Parse response and check if coupon was actually issued
    let couponIssued = false;
    if (response.status === 200) {
        try {
            const responseData = JSON.parse(response.body);
            couponIssued = responseData.success === true;
        } catch (e) {
            console.log('Failed to parse response:', response.body);
        }
    }
    
    // Record coupon success rate
    couponSuccessRate.add(couponIssued);
    
    // Small delay to prevent overwhelming
    sleep(0.01);
}

export function setup() {
    // Initialize test event with stock
    const baseUrl = 'http://host.docker.internal';
    const initResponse = http.post(`${baseUrl}/api/v1/admin/events/k6_stress_test/stock?initial_stock=1000`);
    
    console.log(`Setup: Event initialization returned status ${initResponse.status}`);
    
    if (initResponse.status !== 200) {
        console.log('Setup failed - event initialization error');
    }
    
    return {};
}

export function teardown(data) {
    // Optional: Check final event status
    const baseUrl = 'http://host.docker.internal';
    const statusResponse = http.get(`${baseUrl}/api/v1/coupons/status/k6_stress_test`);
    
    if (statusResponse.status === 200) {
        const status = JSON.parse(statusResponse.body);
        console.log(`Teardown: Final event status - remaining stock: ${status.remaining_stock}`);
    }
}