// k6 load baseline for Nivaro's read-heavy seller API (specs/16 SLO: p95 < 1s).
//   docker run --rm -i -e API=http://host.docker.internal:8190/api/v1 grafana/k6:0.54.0 run - < infra/load/baseline.js
// Setup creates one seller with a product and some orders; virtual users then browse like a seller would.
import http from "k6/http";
import { check, sleep } from "k6";

const API = __ENV.API || "http://localhost:8000/api/v1";
export const options = {
  scenarios: { sellers: { executor: "ramping-vus", startVUs: 0, stages: [{ duration: "20s", target: 20 }, { duration: "60s", target: 20 }, { duration: "10s", target: 0 }] } },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    "http_req_duration{kind:read}": ["p(95)<1000"],
    "http_req_duration{kind:write}": ["p(95)<1500"],
  },
};

function j(r) { try { return r.json(); } catch (e) { return null; } }

export function setup() {
  const stamp = Date.now();
  const email = `k6-${stamp}@example.com`;
  const password = "Load-Test-2083!x";
  http.post(`${API}/auth/register`, JSON.stringify({ email, password, full_name: "Load Test" }), { headers: { "Content-Type": "application/json" } });
  const token = j(http.post(`${API}/auth/login`, JSON.stringify({ email, password, device_name: "k6" }), { headers: { "Content-Type": "application/json" } })).access_token;
  const auth = { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
  const shop = j(http.post(`${API}/merchants`, JSON.stringify({ name: `Load Shop ${stamp}`, currency: "NPR", timezone: "Asia/Kathmandu", default_locale: "en" }), { headers: auth }));
  const merchant = (shop.merchant || shop).id;
  const h = { ...auth, "X-Merchant-Id": merchant };
  const p = j(http.post(`${API}/catalog/products`, JSON.stringify({ title: "Load Kurta", variants: [{ price_minor: 245000, sku: `LOAD-${stamp}` }] }), { headers: h }));
  const vid = p.variants[0].id;
  http.post(`${API}/inventory/variants/${vid}/receive`, JSON.stringify({ quantity: 100000 }), { headers: h });
  return { h, vid };
}

const address = { recipient_name: "Customer", phone: "9841000011", district: "Lalitpur", municipality: "Lalitpur Metropolitan City", ward: 3, area: "Pulchowk" };

export default function (d) {
  const read = { headers: d.h, tags: { kind: "read" } };
  const reads = ["/orders", "/catalog/products", "/inventory/low-stock", "/exceptions", "/twin/summary", "/intelligence/recommendations", "/conversations"];
  for (const path of reads) {
    const r = http.get(`${API}${path}`, { ...read, tags: { kind: "read", name: path } });
    check(r, { [`${path} 200`]: (x) => x.status === 200 });
  }
  if (Math.random() < 0.2) {
    const r = http.post(`${API}/orders`, JSON.stringify({ lines: [{ variant_id: d.vid, quantity: 1 }], address }), { headers: d.h, tags: { kind: "write", name: "POST /orders" } });
    check(r, { "order 201": (x) => x.status === 201 });
  }
  sleep(1);
}
