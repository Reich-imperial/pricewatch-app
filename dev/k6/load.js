import http from 'k6/http';
import { check } from 'k6';

const SYMBOLS = ['RICE_50KG', 'BEANS_50KG', 'GARRI_50KG', 'TOMATO_BASKET', 'PALM_OIL_25L'];

function uuid4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

export const options = {
  scenarios: {
    steady: {
      executor: 'constant-arrival-rate',
      rate: 10,
      timeUnit: '1s',
      duration: '20s',
      preAllocatedVUs: 10,
      maxVUs: 20,
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
  },
};

export default function () {
  const body = JSON.stringify({
    schema_version: 1,
    event_id: uuid4(),
    symbol: SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)],
    price_ngn: 80000 + Math.floor(Math.random() * 20000),
    observed_at: new Date().toISOString(),
    source: 'k6',
  });
  const res = http.post(`${__ENV.BASE_URL}/v1/prices`, body, {
    headers: { 'Content-Type': 'application/json' },
  });
  check(res, { 'status is 202': (r) => r.status === 202 });
}
