#!/usr/bin/env python3
"""
Feasibility scraper v2 — smarter approach after v1 findings.

v1 learned:
  - GeM bid listings are JS-rendered, but bidplus.gem.gov.in has a search endpoint
  - MCA CDM master data needs CAPTCHA; use the MCA V2 API instead  
  - MSME dashboard is JS-rendered; try direct API or SSL bypass

This version:
  1. GeM: Hit the actual bid search endpoint + scrape CPPP eProcure
  2. MCA: Use the MCA V2 company search API or the CDM API endpoints
  3. MSME: Try the dashboard API with SSL verify=False

Still limited to 4-5 results, polite delays.
"""

import requests
import json
import time
import re
import csv
import io
from datetime import datetime
from bs4 import BeautifulSoup
from pathlib import Path
import urllib3

# Suppress only the InsecureRequestWarning (for gov sites with bad certs)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
}

MAX_RESULTS = 5
DELAY = 4


def polite_get(url, session=None, extra_headers=None, timeout=25, verify=True):
    """GET with delay and error handling."""
    time.sleep(DELAY)
    s = session or requests.Session()
    hdrs = {**HEADERS, **(extra_headers or {})}
    try:
        resp = s.get(url, headers=hdrs, timeout=timeout, verify=verify)
        resp.raise_for_status()
        return resp
    except Exception as e:
        print(f"  ⚠ Request failed for {url[:80]}...: {e}")
        return None


def polite_post(url, data=None, json_data=None, session=None, extra_headers=None,
                timeout=25, verify=True):
    """POST with delay and error handling."""
    time.sleep(DELAY)
    s = session or requests.Session()
    hdrs = {**HEADERS, **(extra_headers or {})}
    try:
        resp = s.post(url, headers=hdrs, data=data, json=json_data,
                      timeout=timeout, verify=verify)
        resp.raise_for_status()
        return resp
    except Exception as e:
        print(f"  ⚠ POST failed for {url[:80]}...: {e}")
        return None


def save_results(filename, data):
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    count = len(data.get("results", []))
    print(f"  ✅ Saved {count} results → {path}")


# ===========================================================================
# 1. GeM — Multiple approaches
# ===========================================================================
def scrape_gem_bids():
    print("\n" + "=" * 60)
    print("🏛️  GeM — Government e-Marketplace (Active Bids)")
    print("=" * 60)

    all_bids = []
    session = requests.Session()

    # --- Approach 1: GeM bid search API ---
    # The bidplus site uses an AJAX call to fetch bids
    print("\n  🔍 Trying GeM bid search API...")
    search_keywords = ["brass trophy", "brass memento", "handicraft decor"]

    for keyword in search_keywords:
        if len(all_bids) >= MAX_RESULTS:
            break

        # GeM's bidplus uses this URL pattern for search
        search_url = "https://bidplus.gem.gov.in/all-bids"
        resp = polite_get(search_url, session=session)
        if resp:
            soup = BeautifulSoup(resp.text, "lxml")

            # Check if there's an AJAX/API endpoint in the page scripts
            for script in soup.find_all("script"):
                text = script.string or ""
                # Look for API URLs
                urls = re.findall(r'["\'](/bidlists[^"\']*)["\']', text)
                if urls:
                    print(f"    Found bid list endpoint: {urls[0]}")

                # Look for CSRF/token
                token_match = re.search(r'token["\s:]+["\']([^"\']+)', text, re.I)
                if token_match:
                    print(f"    Found token")

    # --- Approach 2: Scrape the actual bid list ---
    # The all-bids page loads bids via /bidlists with pagination
    print("\n  📋 Trying GeM bid list with search...")
    bid_search_url = "https://bidplus.gem.gov.in/bidlists"
    bid_params = {
        "bidSearchType": "active",
        "searchterm": "brass",
    }
    resp = polite_get(
        f"{bid_search_url}?{'&'.join(f'{k}={v}' for k,v in bid_params.items())}",
        session=session,
        extra_headers={"X-Requested-With": "XMLHttpRequest",
                       "Accept": "text/html, */*; q=0.01"},
    )
    if resp and resp.text.strip():
        soup = BeautifulSoup(resp.text, "lxml")
        # Parse bid cards
        bid_blocks = soup.find_all("div", class_=re.compile(r"bid", re.I))
        print(f"    Found {len(bid_blocks)} bid blocks from search")

        for block in bid_blocks[:MAX_RESULTS]:
            bid = {"source": "GeM_BidSearch"}
            # Extract text content
            bid["text"] = block.get_text(strip=True, separator=" | ")[:500]
            # Look for bid numbers (GEM/2026/B/...)
            bid_no_match = re.search(r'GEM/\d{4}/B/\d+', block.get_text())
            if bid_no_match:
                bid["bid_number"] = bid_no_match.group()
            # Look for links
            links = block.find_all("a", href=True)
            if links:
                bid["url"] = links[0]["href"]
            all_bids.append(bid)

    # --- Approach 3: Central Public Procurement Portal (CPPP) ---
    # This is eProcure.gov.in — reliable, public, HTML tables
    if len(all_bids) < MAX_RESULTS:
        print("\n  📋 Trying CPPP (eprocure.gov.in)...")

        # CPPP uses a search form — try the active tenders page
        cppp_url = "https://eprocure.gov.in/eprocure/app"
        search_params = {
            "page": "FrontEndLatestActiveTenders",
            "service": "page",
        }
        resp = polite_get(
            f"{cppp_url}?{'&'.join(f'{k}={v}' for k,v in search_params.items())}",
            session=session,
        )
        if resp:
            soup = BeautifulSoup(resp.text, "lxml")
            tables = soup.find_all("table")
            print(f"    Found {len(tables)} tables on CPPP page")

            for table in tables:
                if len(all_bids) >= MAX_RESULTS:
                    break
                rows = table.find_all("tr")
                if len(rows) < 2:
                    continue

                # Get headers
                header_cells = rows[0].find_all(["th", "td"])
                headers = [h.get_text(strip=True)[:50] for h in header_cells]

                for row in rows[1:]:
                    cells = row.find_all("td")
                    if len(cells) >= 3:
                        row_data = [c.get_text(strip=True)[:200] for c in cells]
                        tender = dict(zip(headers, row_data)) if headers else {"cells": row_data}
                        tender["source"] = "CPPP_eProcure"

                        # Check if any link
                        link = row.find("a", href=True)
                        if link:
                            href = link["href"]
                            if not href.startswith("http"):
                                href = f"https://eprocure.gov.in{href}"
                            tender["url"] = href

                        all_bids.append(tender)
                        if len(all_bids) >= MAX_RESULTS:
                            break

    # --- Approach 4: GeM search on marketplace ---
    if len(all_bids) < MAX_RESULTS:
        print("\n  🛒 Trying GeM marketplace product search...")
        for term in ["brass+trophy", "brass+statue", "metal+handicraft"]:
            if len(all_bids) >= MAX_RESULTS:
                break
            url = f"https://mkp.gem.gov.in/search?q={term}"
            resp = polite_get(url, session=session)
            if resp:
                soup = BeautifulSoup(resp.text, "lxml")
                # Look for product listings
                products = soup.find_all(["div", "li", "article"],
                                        class_=re.compile(r"product|item|result|listing", re.I))
                for prod in products[:MAX_RESULTS - len(all_bids)]:
                    text = prod.get_text(strip=True, separator=" | ")[:300]
                    if len(text) > 30:
                        all_bids.append({
                            "source": "GeM_Marketplace",
                            "search_term": term.replace("+", " "),
                            "text": text,
                        })

    result = {
        "source": "GeM / CPPP Government Tenders",
        "scraped_at": datetime.now().isoformat(),
        "total_found": len(all_bids),
        "results": all_bids,
        "feasibility_notes": {
            "gem_bidplus": "Bid listings are loaded via AJAX; need to hit /bidlists endpoint with search",
            "cppp": "eProcure.gov.in has HTML tables of active tenders — most reliable for scraping",
            "gem_marketplace": "Product search on mkp.gem.gov.in — shows sellers/products, not tenders",
        },
    }
    save_results("gem_bids.json", result)
    return result


# ===========================================================================
# 2. MCA — Company info
# ===========================================================================
def scrape_mca_companies():
    print("\n" + "=" * 60)
    print("🏢  MCA — Ministry of Corporate Affairs")
    print("=" * 60)

    all_companies = []
    session = requests.Session()

    # --- Approach 1: MCA V2 API (company name search) ---
    # MCA21 V2 had a public API for company search
    print("\n  🔍 Trying MCA company name search...")

    # Keywords relevant to our business
    company_keywords = ["handicraft", "brass", "gift", "decor", "trophy"]

    for keyword in company_keywords[:2]:  # only try 2 to be polite
        if len(all_companies) >= MAX_RESULTS:
            break

        # MCA21 V3 uses this API pattern
        api_url = f"https://www.mca.gov.in/mcafoportal/companyLLPMasterData.do"
        resp = polite_get(api_url, session=session)
        if resp:
            print(f"    Got response from MCA portal ({len(resp.text)} bytes)")
            soup = BeautifulSoup(resp.text, "lxml")

            # Look for any form action or API endpoint
            forms = soup.find_all("form")
            for form in forms:
                action = form.get("action", "")
                if action:
                    print(f"    Found form action: {action}")

    # --- Approach 2: MCA CDM Data Trends (public page, extract JS data) ---
    print("\n  📊 Fetching MCA CDM data trends (extracting chart data)...")
    resp = polite_get("https://mcacdm.nic.in/data-trends", session=session)
    if resp:
        soup = BeautifulSoup(resp.text, "lxml")

        # The CDM pages use Highcharts — data is embedded in <script> tags
        for script in soup.find_all("script"):
            text = script.string or ""
            if len(text) < 100:
                continue

            # Look for Highcharts series data
            # Pattern: categories: ['2020', '2021', ...]
            cat_matches = re.findall(r"categories\s*:\s*\[([^\]]+)\]", text)
            # Pattern: data: [1234, 5678, ...]
            data_matches = re.findall(r"data\s*:\s*\[([^\]]+)\]", text)
            # Pattern: name: 'Series Name'
            name_matches = re.findall(r"name\s*:\s*['\"]([^'\"]+)['\"]", text)

            if cat_matches or data_matches:
                chart_entry = {
                    "source": "MCA_CDM_ChartData",
                    "type": "registration_trends",
                }

                if cat_matches:
                    cats = [c.strip().strip("'\"") for c in cat_matches[0].split(",")]
                    chart_entry["years"] = cats[:15]

                if data_matches:
                    for i, dm in enumerate(data_matches[:3]):
                        vals = [v.strip() for v in dm.split(",") if v.strip()]
                        label = name_matches[i] if i < len(name_matches) else f"series_{i}"
                        chart_entry[f"data_{label}"] = vals[:15]

                if len(chart_entry) > 3:
                    all_companies.append(chart_entry)

            # Also look for raw JSON objects
            json_matches = re.findall(r"(\{[^{}]{100,800}\})", text)
            for jm in json_matches[:1]:
                try:
                    parsed = json.loads(jm)
                    if isinstance(parsed, dict) and len(parsed) > 2:
                        all_companies.append({
                            "source": "MCA_CDM_EmbeddedJSON",
                            "data": parsed,
                        })
                except json.JSONDecodeError:
                    pass

    # --- Approach 3: Try the CDM API directly ---
    print("\n  🔌 Trying MCA CDM API endpoints...")
    # The CDM page uses AJAX to load chart data
    cdm_api_urls = [
        "https://mcacdm.nic.in/cdm/get_company_data.php",
        "https://mcacdm.nic.in/cdm/get_registration_data.php",
        "https://mcacdm.nic.in/cdm/get_economic_activity.php",
    ]
    for api_url in cdm_api_urls:
        if len(all_companies) >= MAX_RESULTS:
            break

        resp = polite_get(api_url, session=session)
        if resp:
            try:
                data = resp.json()
                all_companies.append({
                    "source": "MCA_CDM_API",
                    "endpoint": api_url.split("/")[-1],
                    "data": data if isinstance(data, dict) else data[:5] if isinstance(data, list) else str(data)[:500],
                })
                print(f"    ✅ Got data from {api_url.split('/')[-1]}")
            except json.JSONDecodeError:
                if len(resp.text) > 50:
                    print(f"    Got non-JSON response ({len(resp.text)} bytes)")

    result = {
        "source": "MCA (Ministry of Corporate Affairs)",
        "scraped_at": datetime.now().isoformat(),
        "total_found": len(all_companies),
        "results": all_companies,
        "feasibility_notes": {
            "mca_portal": "mca.gov.in blocks scrapers (403). Need browser automation or their API.",
            "cdm_master_data": "Master data CSV export at mcacdm.nic.in requires CAPTCHA — can't automate easily.",
            "cdm_charts": "Chart data on CDM pages is in Highcharts JS — extractable but fragile.",
            "recommendation": "For production: use the CDM Master Data download manually (it's a big CSV), or buy data from licensed vendors like Probe42, Tofler, or Zaubacorp.",
        },
    }
    save_results("mca_companies.json", result)
    return result


# ===========================================================================
# 3. MSME Dashboard — Udyam stats
# ===========================================================================
def scrape_msme_dashboard():
    print("\n" + "=" * 60)
    print("🏭  MSME — Udyam Registration Dashboard")
    print("=" * 60)

    all_data = []
    session = requests.Session()

    # --- Approach 1: MSME Dashboard with SSL bypass ---
    # Many Indian gov sites have certificate issues
    print("\n  📊 Fetching MSME dashboard (SSL bypass for gov cert issues)...")
    resp = polite_get("https://dashboard.msme.gov.in", session=session, verify=False)
    if resp:
        soup = BeautifulSoup(resp.text, "lxml")

        # Look for Angular/React API calls in scripts
        for script in soup.find_all("script"):
            text = script.string or ""
            if len(text) < 50:
                continue

            # Find API URLs
            api_urls = re.findall(r'["\']?(https?://[^"\'>\s]*api[^"\'>\s]*)["\']?', text, re.I)
            if api_urls:
                all_data.append({
                    "source": "MSME_Dashboard_APIs",
                    "api_endpoints": list(set(api_urls))[:5],
                })

            # Find data objects
            json_matches = re.findall(r'(\{[^{}]{50,500}\})', text)
            for jm in json_matches[:2]:
                try:
                    parsed = json.loads(jm)
                    if isinstance(parsed, dict):
                        all_data.append({
                            "source": "MSME_Dashboard_Data",
                            "data": parsed,
                        })
                except json.JSONDecodeError:
                    pass

        # Look for embedded stats
        stats = soup.find_all(string=re.compile(r'\d+[,.]?\d*\s*(?:lakh|crore|million|total)', re.I))
        for stat in stats[:MAX_RESULTS]:
            all_data.append({
                "source": "MSME_Dashboard_Stat",
                "text": stat.strip()[:200],
            })

    # --- Approach 2: Try the MSME Smartboard API directly ---
    print("\n  🔌 Trying MSME API endpoints...")
    msme_apis = [
        "https://dashboard.msme.gov.in/api/dashboard",
        "https://dashboard.msme.gov.in/api/udyam",
        "https://dashboard.msme.gov.in/api/summary",
        "https://dashboard.msme.gov.in/dashboard/api/summary",
    ]
    for api_url in msme_apis[:3]:
        if len(all_data) >= MAX_RESULTS:
            break

        resp = polite_get(api_url, session=session, verify=False,
                         extra_headers={"Accept": "application/json"})
        if resp:
            try:
                data = resp.json()
                all_data.append({
                    "source": "MSME_API",
                    "endpoint": api_url,
                    "data": data if isinstance(data, (dict, list)) else str(data)[:500],
                })
                print(f"    ✅ Got JSON from: {api_url}")
            except json.JSONDecodeError:
                if len(resp.text) > 50 and resp.text.strip()[:1] not in ["<", "!"]:
                    print(f"    Got non-JSON response ({len(resp.text)} bytes)")

    # --- Approach 3: Udyam portal page (already worked in v1) ---
    print("\n  📋 Fetching Udyam registration portal info...")
    resp = polite_get("https://udyamregistration.gov.in", session=session, verify=False)
    if resp:
        soup = BeautifulSoup(resp.text, "lxml")

        # Get meaningful stats/numbers
        for el in soup.find_all(["h1", "h2", "h3", "h4", "strong", "b", "span"]):
            text = el.get_text(strip=True)
            # Only capture if it has numbers or registration-related keywords
            if (re.search(r'\d', text) and len(text) > 10 and len(text) < 200) or \
               any(kw in text.lower() for kw in ["registered", "total udyam", "manufacturing", "active"]):
                all_data.append({
                    "source": "Udyam_Portal",
                    "text": text,
                })
                if len(all_data) >= MAX_RESULTS * 2:
                    break

    # --- Approach 4: data.gov.in MSME dataset ---
    print("\n  📂 Trying data.gov.in for MSME datasets...")
    resp = polite_get(
        "https://data.gov.in/resource/district-wise-count-udyam-registered-msmes",
        session=session,
    )
    if resp:
        soup = BeautifulSoup(resp.text, "lxml")
        # Look for download links
        download_links = soup.find_all("a", href=re.compile(r'\.csv|\.xlsx|download', re.I))
        if download_links:
            all_data.append({
                "source": "DataGovIn_MSME",
                "download_links": [
                    {"text": a.get_text(strip=True), "href": a["href"]}
                    for a in download_links[:3]
                ],
            })

    result = {
        "source": "MSME / Udyam Dashboard",
        "scraped_at": datetime.now().isoformat(),
        "total_found": len(all_data),
        "results": all_data,
        "feasibility_notes": {
            "dashboard": "dashboard.msme.gov.in is JS-rendered (Angular/React). Need to find the API endpoints it calls.",
            "ssl_issue": "Gov site has SSL cert issues — verify=False needed.",
            "udyam_portal": "Landing page has general info but no searchable data.",
            "recommendation": "For production: use data.gov.in bulk datasets for MSME stats, or the MSME Smartboard API once endpoints are discovered.",
        },
    }
    save_results("msme_udyam.json", result)
    return result


# ===========================================================================
# Main
# ===========================================================================
def main():
    print("🚀 Data Feasibility Scraper v2 — Moradabad Handicraft Project")
    print(f"   Max results per source: {MAX_RESULTS}")
    print(f"   Delay between requests: {DELAY}s")
    print(f"   Output directory: {OUTPUT_DIR}")
    print(f"   Time: {datetime.now().isoformat()}")

    results = {}

    for name, fn in [("gem", scrape_gem_bids),
                      ("mca", scrape_mca_companies),
                      ("msme", scrape_msme_dashboard)]:
        try:
            results[name] = fn()
        except Exception as e:
            print(f"\n  ❌ {name.upper()} scraping failed: {e}")
            import traceback
            traceback.print_exc()
            results[name] = {"error": str(e), "total_found": 0}

    # Summary
    print("\n" + "=" * 60)
    print("📊 FEASIBILITY SUMMARY")
    print("=" * 60)
    for source, data in results.items():
        count = data.get("total_found", 0)
        status = "✅" if count > 0 else "⚠️  No data"
        notes = data.get("feasibility_notes", {})
        rec = notes.get("recommendation", "")
        print(f"\n  {source.upper():6s} → {status} ({count} items)")
        if rec:
            print(f"         💡 {rec[:120]}")

    print(f"\n  Output files:")
    for f in sorted(OUTPUT_DIR.glob("*.json")):
        size = f.stat().st_size
        print(f"    📄 {f.name} ({size:,} bytes)")

    print("\n✨ Done!")


if __name__ == "__main__":
    main()

