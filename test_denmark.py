"""Quick test: Denmark scrape to verify geolocation fix."""
import time, sys, requests

API = "http://localhost:8000"

print("=" * 60)
print("  TEST: Denmark geolocation fix")
print("=" * 60)

resp = requests.post(f"{API}/api/start", json={
    "country": "Denmark",
    "city": "Copenhagen",
    "company_types": ["clothing brand"],
    "radius_km": 25,
    "min_score": 3,
})
session_id = resp.json()["session_id"]
print(f"Session: {session_id}\n")

start = time.time()
last = ""
while time.time() - start < 300:
    pr = requests.get(f"{API}/api/progress/{session_id}").json()
    if pr.get("current_action") != last:
        last = pr["current_action"]
        print(f"  [{int(time.time()-start):>3}s] {pr['status']:12s} | {last}")
    if pr["status"] in ("completed", "failed"):
        break
    time.sleep(1)

results = requests.get(f"{API}/api/results/{session_id}").json()
print(f"\n{'=' * 60}")
print(f"  LEADS: {len(results)}")
print(f"{'=' * 60}")
for i, l in enumerate(results, 1):
    print(f"\n  #{i} {l['company_name']}")
    print(f"     📍 {l['city']}, {l['country']}")
    print(f"     🌐 {l['website']}")
    print(f"     📧 {l['likely_email']}")
    print(f"     📞 {l['phone']}")
    print(f"     ⭐ {l['icp_score']}/10 {l['tier']}")
