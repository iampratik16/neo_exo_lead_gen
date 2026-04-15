"""
Test script for Neo Eco Cleaning Lead Generator — runs a real scrape
against Google Maps. Polls for progress and prints all leads found.
"""
import time
import sys
import requests

API = "http://localhost:8000"


def main():
    print("=" * 60)
    print("  NEO ECO CLEANING — LEAD GENERATOR LIVE TEST")
    print("=" * 60)

    payload = {"dry_run": False}

    print(f"\n📍 Target   : London — North London boroughs")
    print(f"🔎 Queries  : 46 (Property Management + Estate/Letting Agents)")
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

    # Poll for progress — timeout after 10 minutes (46 queries need more time)
    start = time.time()
    timeout = 600
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
        print("\n⏰ Timed out after 10 minutes.")

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
        print(f"  Lead #{i}: {lead['business_name']}")
        print(f"  🏢 Category: {lead['category']}")
        print(f"  📍 Borough : {lead['borough']} ({lead['area_zone']})")
        print(f"  📞 Phone   : {lead['phone']}")
        print(f"  📧 Email   : {lead['email']}")
        print(f"  🌐 Website : {lead['website']}")
        print(f"  ⭐ Rating  : {lead['rating']} ({lead['review_count']} reviews)")
        print(f"  🎯 Priority: {lead['outreach_priority']} — {lead['icp_tier']}")

    # Summary
    high = sum(1 for l in results if l["outreach_priority"] == "HIGH")
    medium = sum(1 for l in results if l["outreach_priority"] == "MEDIUM")
    low = sum(1 for l in results if l["outreach_priority"] == "LOW")
    has_email = sum(1 for l in results if l["email"])

    print(f"\n{'=' * 60}")
    print(f"  SUMMARY")
    print(f"  Total: {len(results)} | 🟢 HIGH: {high} | 🟡 MEDIUM: {medium} | 🔴 LOW: {low}")
    print(f"  With email: {has_email}/{len(results)}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
