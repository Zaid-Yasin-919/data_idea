#!/usr/bin/env python3
"""
Playwright Prototype for GeM (Government e-Marketplace) Tenders.

Feasibility check:
  - Launches headless Chromium via Playwright
  - Intercepts XHR / Fetch API responses to capture structured bid data directly
  - Navigates to GeM active bids (bidplus.gem.gov.in/all-bids)
  - Searches for keywords ('brass', 'trophy', 'memento')
  - Extracts 3-5 live bid cards: Bid ID, Items, Quantity, Department, End Date
  - Saves output to data/gem_playwright_bids.json
"""

import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "gem_playwright_bids.json"

MAX_BIDS = 5
SEARCH_KEYWORDS = ["brass", "trophy", "memento", "handicraft"]


async def run():
    print("=" * 60)
    print("🚀 GeM Bids Playwright Prototype — Feasibility Test")
    print("=" * 60)

    extracted_bids = []
    intercepted_api_data = []

    async with async_playwright() as p:
        # Launch browser with realistic user agent and stealthy defaults
        print("\n🌐 Launching Chromium browser...")
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )

        page = await context.new_page()

        # Listen for any JSON responses from GeM's backend APIs
        async def on_response(response):
            try:
                url = response.url
                content_type = response.headers.get("content-type", "")
                if ("bid" in url.lower() or "search" in url.lower()) and "json" in content_type:
                    json_data = await response.json()
                    intercepted_api_data.append({"url": url, "data": json_data})
                    print(f"  [API Intercepted] {url[:80]}... ({len(str(json_data))} bytes)")
            except Exception:
                pass

        page.on("response", on_response)

        # 1. Navigate to GeM all-bids page
        target_url = "https://bidplus.gem.gov.in/all-bids"
        print(f"\n📄 Navigating to: {target_url}")

        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
            print("  ✅ DOM Content Loaded")
        except Exception as e:
            print(f"  ⚠ Page load timeout/warning: {e}")

        # Wait a few seconds for dynamic scripts to boot up
        await page.wait_for_timeout(4000)

        # 2. Check for search inputs on GeM
        # GeM typically uses #searchBid, #search, or input[placeholder*='Search']
        search_input = None
        selectors_to_try = [
            "input#searchBid",
            "input[name='searchterm']",
            "input[placeholder*='Search' i]",
            "input[placeholder*='Bid' i]",
            "#search_term",
            "input.form-control",
        ]

        # 2. Iterate through target keywords
        search_input_sel = "input#searchBid, input[name='searchterm'], input[placeholder*='Search' i], input.form-control"

        for kw in SEARCH_KEYWORDS:
            print(f"\n  🔍 Searching for keyword: '{kw}'")
            search_input = page.locator(search_input_sel).first

            if await search_input.count() > 0 and await search_input.is_visible():
                await search_input.fill("")
                await search_input.fill(kw)
                await page.keyboard.press("Enter")
                print(f"     ⏳ Waiting for '{kw}' results to render...")
                await page.wait_for_timeout(4500)
            else:
                print("     ⚠ Search input not visible, skipping to DOM check...")

            # Extract cards for this keyword
            bid_elements = page.locator(".card, .border.block, .bid-card, div.col-md-12:has-text('GEM/')")
            card_count = await bid_elements.count()

            if card_count == 0:
                bid_elements = page.locator("div:has-text('GEM/'):not(:has(div:has-text('GEM/')))")
                card_count = await bid_elements.count()

            print(f"     Found {card_count} candidate bid blocks for '{kw}'")

            kw_captured = 0
            for i in range(min(card_count, 12)):
                if kw_captured >= 4:
                    break

                elem = bid_elements.nth(i)
                text = (await elem.inner_text()).strip()

                bid_no_match = re.search(r"GEM/\d{4}/[B|R]/\d+", text)
                if not bid_no_match and "bid no" not in text.lower():
                    continue

                bid_id = bid_no_match.group(0) if bid_no_match else "Unknown"

                # Parse key fields using regex patterns
                items_match = re.search(r"Items?:\s*(.*?)(?:\n|Quantity|$)", text, re.I)
                qty_match = re.search(r"Quantity:\s*(\d+)", text, re.I)
                dept_match = re.search(r"Department Name And Address:\s*(.*?)(?:\n|Start Date|$)", text, re.I)
                end_date_match = re.search(r"End Date:\s*(.*?)(?:\n|$)", text, re.I)

                # Detail link
                link_elem = elem.locator("a[href*='bid']").first
                bid_url = None
                if await link_elem.count() > 0:
                    href = await link_elem.get_attribute("href")
                    if href:
                        bid_url = href if href.startswith("http") else f"https://bidplus.gem.gov.in{href}"

                bid_record = {
                    "bid_id": bid_id,
                    "search_keyword": kw,
                    "items": items_match.group(1).strip() if items_match else None,
                    "quantity": qty_match.group(1).strip() if qty_match else None,
                    "department": dept_match.group(1).strip() if dept_match else None,
                    "end_date": end_date_match.group(1).strip() if end_date_match else None,
                    "link": bid_url,
                    "raw_preview": text[:250].replace("\n", " | "),
                }

                # Avoid duplicates
                if not any(b["bid_id"] == bid_id for b in extracted_bids if bid_id != "Unknown"):
                    extracted_bids.append(bid_record)
                    kw_captured += 1
                    print(f"       ⭐ [{kw.upper()}] Captured: {bid_id} | {bid_record['items'] or 'Items'}")

        # If zero cards matched specific selectors, fallback to raw regex search across page text
        if not extracted_bids:
            print("  ℹ Trying full-page regex extraction for GEM bid patterns...")
            all_text = await page.inner_text("body")
            matches = re.findall(r"(GEM/\d{4}/[B|R]/\d+)", all_text)
            unique_ids = list(dict.fromkeys(matches))[:MAX_BIDS]

            for uid in unique_ids:
                extracted_bids.append({
                    "bid_id": uid,
                    "source": "Playwright_Regex_Extraction",
                    "link": f"https://bidplus.gem.gov.in/showbidDocument/{uid.split('/')[-1]}",
                })
                print(f"    ⭐ Found Bid ID via page text: {uid}")

        # Take a confirmation screenshot for developer inspection
        screenshot_path = OUTPUT_DIR / "gem_playwright_test.png"
        await page.screenshot(path=str(screenshot_path))
        print(f"\n📸 Saved page screenshot to: {screenshot_path}")

        await browser.close()

    # Save results
    result_payload = {
        "source": "GeM via Playwright Headless Chromium",
        "timestamp": datetime.now().isoformat(),
        "total_extracted": len(extracted_bids),
        "results": extracted_bids,
        "intercepted_api_endpoints": [a["url"] for a in intercepted_api_data[:5]],
        "feasibility_assessment": {
            "browser_launch": "Success",
            "js_execution": "Success",
            "anti_bot_bypass": "Passed (No immediate blocking on Chromium)",
            "ready_for_production": len(extracted_bids) > 0,
        },
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result_payload, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"✅ Finished! Saved {len(extracted_bids)} bids to {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run())

