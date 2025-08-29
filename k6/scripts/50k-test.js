import http from 'k6/http';
import { check } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const couponSuccessRate = new Rate('coupon_success_rate');
const couponResponseTime = new Trend('coupon_response_time');
const totalCouponsIssued = new Counter('total_coupons_issued');

// 50K users test
export const options = {
    scenarios: {
        fifty_k_test: {
            executor: 'per-vu-iterations',
            vus: 50000, // 50K unique users
            iterations: 1, // Each user makes 1 request
            maxDuration: '10m',
        }
    },
    thresholds: {
        'http_req_failed': ['rate<0.20'],
        'http_req_duration': ['p(95)<10000'],
        'coupon_success_rate': ['rate>=0.01'],
    },
};

function generateUserId() {
    return `user_${String(__VU).padStart(6, '0')}_${Math.random().toString(36).substr(2, 8)}`;
}

export default function () {
    const baseUrl = 'http://host.docker.internal';
    const payload = JSON.stringify({
        user_id: generateUserId(),
        event_id: 'new_year_2025'
    });

    const headers = {
        'Content-Type': 'application/json',
    };

    const response = http.post(`${baseUrl}/api/v1/coupons/issue`, payload, { headers });
    
    couponResponseTime.add(response.timings.duration);
    
    check(response, {
        'status is 200': (r) => r.status === 200,
        'response time < 10000ms': (r) => r.timings.duration < 10000,
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
            // Parse errors ignored under load
        }
    }
    
    couponSuccessRate.add(couponIssued);
}

export function setup() {
    console.log('🚀 EXTREME TEST: 50,000 users competing for 5,000 coupons');
    console.log('⚠️  Testing system breaking point!');
    
    const baseUrl = 'http://host.docker.internal';
    const initResponse = http.post(`${baseUrl}/api/v1/admin/events/new_year_2025/stock?initial_stock=5000`);
    
    console.log(`Setup: Event initialization returned status ${initResponse.status}`);
    return { startTime: new Date().getTime() };
}

export function teardown(data) {
    const endTime = new Date().getTime();
    const totalTestTime = (endTime - data.startTime) / 1000;
    
    console.log(`🏁 50K test completed in ${totalTestTime.toFixed(2)} seconds`);
    
    const baseUrl = 'http://host.docker.internal';
    const statusResponse = http.get(`${baseUrl}/api/v1/coupons/status/new_year_2025`);
    
    if (statusResponse.status === 200) {
        try {
            const status = JSON.parse(statusResponse.body);
            const couponsIssued = 5000 - status.remaining_stock;
            console.log(`📊 Final: 50K users → ${couponsIssued}/5000 coupons (${(couponsIssued/50000*100).toFixed(2)}%)`);
        } catch (e) {
            console.log('Could not parse final status');
        }
    }
}