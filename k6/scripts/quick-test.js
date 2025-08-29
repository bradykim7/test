import http from 'k6/http';
import { check } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const couponSuccessRate = new Rate('coupon_success_rate');
const couponResponseTime = new Trend('coupon_response_time');
const totalCouponsIssued = new Counter('total_coupons_issued');

// Quick test: 2000 unique users, each making 1 request = 200 RPS
export const options = {
    scenarios: {
        quick_test: {
            executor: 'per-vu-iterations',
            vus: 2000, // 2000 unique users
            iterations: 1, // Each user makes 1 request
            maxDuration: '30s',
        }
    },
    thresholds: {
        'http_req_failed': ['rate<0.10'],
        'http_req_duration': ['p(95)<1000'],
        'coupon_success_rate': ['rate>=0.01'],
    },
};

function generateUserId() {
    // Each VU gets a unique ID (no iteration number since each user makes only 1 request)
    return `unique_user_${__VU}_${Math.random().toString(36).substr(2, 8)}`;
}

export default function () {
    const baseUrl = 'http://host.docker.internal';
    const payload = JSON.stringify({
        user_id: generateUserId(),
        event_id: 'summer_sale_2024'
    });

    const headers = {
        'Content-Type': 'application/json',
    };

    const response = http.post(`${baseUrl}/api/v1/coupons/issue`, payload, { headers });
    
    couponResponseTime.add(response.timings.duration);
    
    check(response, {
        'status is 200': (r) => r.status === 200,
        'response time < 1000ms': (r) => r.timings.duration < 1000,
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
            // Ignore parse errors
        }
    }
    
    couponSuccessRate.add(couponIssued);
}

export function setup() {
    console.log('🚀 Quick Test: 2000 unique users, each making 1 request');
    
    const baseUrl = 'http://host.docker.internal';
    const initResponse = http.post(`${baseUrl}/api/v1/admin/events/summer_sale_2024/stock?initial_stock=1000`);
    
    console.log(`Setup: Event initialization returned status ${initResponse.status}`);
    return {};
}

export function teardown(data) {
    const baseUrl = 'http://host.docker.internal';
    const statusResponse = http.get(`${baseUrl}/api/v1/coupons/status/summer_sale_2024`);
    
    if (statusResponse.status === 200) {
        try {
            const status = JSON.parse(statusResponse.body);
            console.log(`📊 Final: Remaining stock: ${status.remaining_stock}, Issued: ${1000 - status.remaining_stock}`);
        } catch (e) {
            console.log('Could not parse final status');
        }
    }
}