import http from 'k6/http';
import { check, sleep } from 'k6';

// 1. 테스트 옵션: 부하 시나리오 설정
export const options = {
    scenarios: {
        peak_load: {
            executor: 'constant-arrival-rate',
            rate: 200, // 초당 req (peak)
            timeUnit: '1s',
            duration: '1m',
            preAllocatedVUs: 500,
            maxVUs: 500,
            gracefulStop: '30s',
            exec: 'peak_load',
        }
    },
  // thresholds는 테스트의 성공/실패 기준을 정의합니다.
    thresholds: {
        'http_req_failed': ['rate<0.01'],   // HTTP 에러율이 1% 미만이어야 합니다.
        'http_req_duration': ['p(95)<800'], // 전체 요청의 95%가 800ms 안에 응답해야 합니다.
    },
};

// 2. 요청에 필요한 데이터 설정
const GET_URL = 'https://test-member.mailplug.com/api/v2/member/default-configs';
const PATCH_URL = 'https://test-member.mailplug.com/api/v2/member/me/configs/skin';
const JWT_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3NTM0Mjc2NTcsImV4cCI6MTc1MzQyOTQ1NywiYWNjb3VudElkIjoyLCJ1c2VybmFtZSI6Im1haWx0ZXN0QGd0NTUzMy5teXBsdWcua3IiLCJzY29wZSI6WyJtYWlsIiwiYWRkcmVzc2Jvb2siLCJjYWxlbmRhciIsImJvYXJkIiwic21zIiwib3JnYW5pemF0aW9uIiwibWVzc2VuZ2VyIiwiZWFzIiwid29ya25vdGUiLCJ0YXNrIiwicmVzZXJ2ZSIsImFkbWluIiwiaHJtIl0sInNlcnZpY2VJZCI6MTAwMDAwMDAyOCwiY2xpZW50SVAiOiIyMjAuODUuMjEuMzUiLCJnb29kcyI6IkdXX1NIUkQiLCJhY2NvdW50TmFtZSI6Ilx1YWQwMFx1YjlhY1x1Yzc5MFx1YjJlNCEhISIsImp0aSI6ImQ2MzQifQ.xB1rTi6vNhY7_OyY4BdJcPetzrQluaSiW04vz1TnLGQ';
const PAYLOAD = JSON.stringify({
    skinColor: '1',
    skinDark: '',
    skinLeft: 'white',
    skinRGB: 'orange',
});

const HEADERS = {
    headers: {
        'Authorization': `Bearer ${JWT_TOKEN}`,
        'Content-Type': 'application/json',
    }
};

// 3. 가상 사용자(VU)가 실행할 메인 테스트 함수
export function production_pattern() {
  // 설정된 URL, PAYLOAD, HEADERS GET 요청을 보냅니다.
const res = http.get(GET_URL, HEADERS);

// 응답이 성공했는지 (HTTP Status가 200인지) 확인합니다.
check(res, {
'✅ PATCH request is successful (status 200)': (r) => r.status === 200,
});

  // 다음 요청을 보내기 전 1초간 대기합니다. (사용자의 생각 시간 모방)
  //sleep(1);
}

export function peak_load() {
     // 설정된 URL, PAYLOAD, HEADERS PATCH 요청을 보냅니다.
    // const res = http.patch(PATCH_URL, PAYLOAD, HEADERS);
    const res = http.get(GET_URL, HEADERS);

    // 응답이 성공했는지 (HTTP Status가 200인지) 확인합니다.
    check(res, {
        '✅ PATCH request is successful (status 200)': (r) => r.status === 200,
    });
}