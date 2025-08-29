import http from 'k6/http';
import { check } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const couponSuccessRate = new Rate('coupon_success_rate');
const couponResponseTime = new Trend('coupon_response_time');
const totalCouponsIssued = new Counter('total_coupons_issued');

// Large scale test: 100K unique users competing for limited coupons
export const options = {
    scenarios: {
        large_scale_test: {
            executor: 'per-vu-iterations',
            vus: 100000, // 100K unique users
            iterations: 1, // Each user makes 1 request
            maxDuration: '5m', // Allow up to 5 minutes
        }
    },
    thresholds: {
        'http_req_failed': ['rate<0.05'],    // Less than 5% HTTP failures
        'http_req_duration': ['p(95)<2000'], // 95% under 2 seconds
        'coupon_success_rate': ['rate>=0.10'], // At least 10% should get coupons
    },
};

function generateUserId() {
    // Ensure completely unique user IDs for 100K users
    return `user_${String(__VU).padStart(6, '0')}_${Math.random().toString(36).substr(2, 10)}`;
}

export default function () {
    const baseUrl = 'http://host.docker.internal';
    const payload = JSON.stringify({
        user_id: generateUserId(),
        event_id: 'black_friday_mega_sale'
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
    check(response, {
        'status is 200': (r) => r.status === 200,
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
            console.log('Failed to parse response:', response.body);
        }
    }
    
    couponSuccessRate.add(couponIssued);
}

export function setup() {
    console.log('🚀 LARGE SCALE TEST: 100,000 users competing for limited coupons');
    console.log('⚠️  This will test your system under extreme load!');
    
    // Initialize event with more stock for large scale test
    const baseUrl = 'http://host.docker.internal';
    const initResponse = http.post(`${baseUrl}/api/v1/admin/events/black_friday_mega_sale/stock?initial_stock=10000`);
    
    console.log(`Setup: Event initialization returned status ${initResponse.status}`);
    console.log('📊 Target: 100K users → 10K coupons (10% success rate expected)');
    
    if (initResponse.status !== 200) {
        console.log('❌ Setup failed - event initialization error');
        throw new Error('Event initialization failed');
    }
    
    return { startTime: new Date().getTime() };
}

export function teardown(data) {
    const endTime = new Date().getTime();
    const totalTestTime = (endTime - data.startTime) / 1000;
    
    console.log(`🏁 Large scale test completed in ${totalTestTime.toFixed(2)} seconds`);
    
    // Check final event status
    const baseUrl = 'http://host.docker.internal';
    const statusResponse = http.get(`${baseUrl}/api/v1/coupons/status/black_friday_mega_sale`);
    
    if (statusResponse.status === 200) {
        try {
            const status = JSON.parse(statusResponse.body);
            const couponsIssued = 10000 - status.remaining_stock;
            const successRate = (couponsIssued / 100000 * 100).toFixed(2);
            
            console.log(`📊 Final Results:`);
            console.log(`   - Total users: 100,000`);
            console.log(`   - Coupons issued: ${couponsIssued}`);
            console.log(`   - Remaining stock: ${status.remaining_stock}`);
            console.log(`   - Success rate: ${successRate}%`);
            console.log(`   - Participants: ${status.total_participants}`);
        } catch (e) {
            console.log('Could not parse final status');
        }
    }
}