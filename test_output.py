"""
Test script for Bassi Leads Scraper — runs a real scrape against Google Maps.
Polls for progress and prints all leads found.
"""
import time
import sys
import requests

API = "http://localhost:8000"

def main():
    print("=" * 60)
    print("  BASSI LEADS SCRAPER — LIVE TEST")
    print("=" * 60)

    payload = {
        "country": "United Kingdom",
        "city": "London",
        "company_types": ["clothing brand", "fashion retailer"],
        "radius_km": 25,
        "min_score": 3,  # low threshold so we see all results
    }

    print(f"\n📍 Location : {payload['city']}, {payload['country']}")
    print(f"🔎 Queries  : {payload['company_types']}")
    print(f"⚙️  Min Score: {payload['min_score']}")
    print("-" * 60)

    # Start scrape
    try:
        resp = requests.post(f"{API}/api/start", json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ Could not connect to backend: {e}")
        sys.exit(1)

    session_id = resp.json()["session_id"]
    print(f"🚀 Session started: {session_id}\n")

    # Poll for progress - timeout after 5 minutes
    start = time.time()
    timeout = 300
    last_action = ""

    while time.time() - start < timeout:
        try:
            pr = requests.get(f"{API}/api/progress/{session_id}", timeout=5).json()
        except Exception:
            time.sleep(2)
            continue

        if pr.get("current_action") != last_action:
            last_action = pr["current_action"]
            elapsed = int(time.time() - start)
            print(f"  [{elapsed:>3}s] {pr['status'].upper():12s} | Leads: {pr['leads_found']:>3} | {last_action}")

        if pr["status"] in ("completed", "failed"):
            break
        time.sleep(1)
    else:
        print("\n⏰ Timed out after 5 minutes.")

    # Fetch results
    print("\n" + "=" * 60)
    results = requests.get(f"{API}/api/results/{session_id}", timeout=10).json()
    print(f"  TOTAL LEADS: {len(results)}")
    print("=" * 60)

    if not results:
        print("No leads found. Check backend logs for errors.")
        return

    for i, lead in enumerate(results, 1):
        print(f"\n{'─' * 60}")
        print(f"  Lead #{i}: {lead['company_name']}")
        print(f"  🌐 Website : {lead['website']}")
        print(f"  📧 Email(s): {lead['likely_email']}")
        print(f"  📞 Phone   : {lead['phone']}")
        print(f"  📍 Location: {lead['city']}, {lead['country']}")
        print(f"  ⭐ Score   : {lead['icp_score']}/10  ({lead['tier']})")
        print(f"  🔗 Maps    : {lead['google_maps_url']}")
        print(f"  🏭 Signals : {lead['india_sourcing_signals']}")
        print(f"  💡 Why Hot : {lead['why_hot_lead']}")

    # Summary
    tier1 = sum(1 for l in results if "Tier 1" in l["tier"])
    tier2 = sum(1 for l in results if "Tier 2" in l["tier"])
    tier3 = sum(1 for l in results if "Tier 3" in l["tier"])
    has_email = sum(1 for l in results if "No email" not in l["likely_email"])

    print(f"\n{'=' * 60}")
    print(f"  SUMMARY")
    print(f"  Total: {len(results)} | Tier 1 🔥: {tier1} | Tier 2 ⏳: {tier2} | Tier 3 ❄️: {tier3}")
    print(f"  With real email(s): {has_email}/{len(results)}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
