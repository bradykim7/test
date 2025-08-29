import http from 'k6/http';
import { check } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const couponSuccessRate = new Rate('coupon_success_rate');
const couponResponseTime = new Trend('coupon_response_time');
const totalCouponsIssued = new Counter('total_coupons_issued');

// Medium scale test: 10K unique users competing for 1K coupons
export const options = {
    scenarios: {
        medium_scale_test: {
            executor: 'per-vu-iterations',
            vus: 10000, // 10K unique users
            iterations: 1, // Each user makes 1 request
            maxDuration: '2m',
        }
    },
    thresholds: {
        'http_req_failed': ['rate<0.05'],
        'http_req_duration': ['p(95)<2000'],
        'coupon_success_rate': ['rate>=0.08'], // At least 8% should get coupons
    },
};

function generateUserId() {
    return `user_${String(__VU).padStart(5, '0')}_${Math.random().toString(36).substr(2, 8)}`;
}

export default function () {
    const baseUrl = 'http://host.docker.internal';
    const payload = JSON.stringify({
        user_id: generateUserId(),
        event_id: 'christmas_special'
    });

    const headers = {
        'Content-Type': 'application/json',
    };

    const response = http.post(`${baseUrl}/api/v1/coupons/issue`, payload, { headers });
    
    couponResponseTime.add(response.timings.duration);
    
    check(response, {
        'status is 200': (r) => r.status === 200,
        'response time < 3000ms': (r) => r.timings.duration < 3000,
    });

    let couponIssued = false;
    if (response.status === 200) {
        try {
            const responseData = JSON.parse(response.body);
            couponIssued = responseData.success === true;
            if (couponIssued) {
                totalCouponsIssued.add(1);
            }
        } catch (e) {
            // Parse errors ignored
        }
    }
    
    couponSuccessRate.add(couponIssued);
}

export function setup() {
    console.log('🚀 MEDIUM SCALE TEST: 10,000 users competing for 1,000 coupons');
    
    const baseUrl = 'http://host.docker.internal';
    const initResponse = http.post(`${baseUrl}/api/v1/admin/events/christmas_special/stock?initial_stock=1000`);
    
    console.log(`Setup: Event initialization returned status ${initResponse.status}`);
    return {};
}

export function teardown(data) {
    const baseUrl = 'http://host.docker.internal';
    const statusResponse = http.get(`${baseUrl}/api/v1/coupons/status/christmas_special`);
    
    if (statusResponse.status === 200) {
        try {
            const status = JSON.parse(statusResponse.body);
            const couponsIssued = 1000 - status.remaining_stock;
            console.log(`📊 Final: Users: 10K, Coupons: ${couponsIssued}/1000, Success: ${(couponsIssued/10000*100).toFixed(1)}%`);
        } catch (e) {
            console.log('Could not parse final status');
        }
    }
}