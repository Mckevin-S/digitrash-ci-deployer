import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 10 },   // Ramp-up
    { duration: '2m', target: 50 },     // Charge soutenue
    { duration: '30s', target: 0 },     // Cooldown
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:5000';

export default function () {
  const checks = [
    { name: 'health', url: '/health', status: 200 },
    { name: 'kpi', url: '/api/kpi', status: 200 },
    { name: 'sales', url: '/api/sales', status: 200 },
    { name: 'categories', url: '/api/categories', status: 200 },
  ];
  
  for (const check of checks) {
    const res = http.get(`${BASE_URL}${check.url}`);
    check(res, {
      [`${check.name} status ${check.status}`]: (r) => r.status === check.status,
      [`${check.name} response < 300ms`]: (r) => r.timings.duration < 300,
    });
    sleep(0.5);
  }
}