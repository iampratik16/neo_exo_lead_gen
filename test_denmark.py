"""Quick test: verify the Neo Eco scraper starts and handles a small query set."""
import time
import sys
import requests

API = "http://localhost:8000"

print("=" * 60)
print("  TEST: Neo Eco Cleaning — Quick Scrape Test")
print("=" * 60)

resp = requests.post(f"{API}/api/start", json={"dry_run": False})
session_id = resp.json()["session_id"]
print(f"Session: {session_id}\n")

start = time.time()
last = ""
while time.time() - start < 600:
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
    print(f"\n  #{i} {l['business_name']}")
    print(f"     📍 {l['borough']}, {l['area_zone']}")
    print(f"     🌐 {l['website']}")
    print(f"     📧 {l['email']}")
    print(f"     📞 {l['phone']}")
    print(f"     🎯 {l['outreach_priority']} — {l['icp_tier']}")
