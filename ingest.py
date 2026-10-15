#!/usr/bin/env python3
"""
Ingestion & Normalization Pipeline.

Takes raw JSON scrapes (GeM / CPPP tenders) and MCA CSV exports,
normalizes them into structured entities:
  - organizations (government bodies, gifting firms, décor brands)
  - intent_signals (bids, incorporations)
  - signal_items (line-items demanded)
"""

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import db

DATA_DIR = Path(__file__).parent / "data"


def calculate_moradabad_intent_score(text: str) -> float:
    """
    Computes a relevance score (0.0 to 1.0) indicating how strongly
    this demand matches Moradabad metal handicraft manufacturing.
    """
    text_lower = text.lower()
    score = 0.2  # base score

    # Primary materials
    if any(m in text_lower for m in ["brass", "peetal", "pittal"]):
        score += 0.5
    elif any(m in text_lower for m in ["bronze", "copper", "tamba"]):
        score += 0.35
    elif any(m in text_lower for m in ["aluminium", "aluminum", "cast iron"]):
        score += 0.25

    # Target product categories
    if any(k in text_lower for k in ["trophy", "trophies", "memento", "mementos", "award plaque"]):
        score += 0.35
    elif any(k in text_lower for k in ["statue", "idol", "figurine", "sculpture", "murti"]):
        score += 0.3
    elif any(k in text_lower for k in ["handicraft", "artware", "vase", "planter", "candle stand"]):
        score += 0.25
    elif any(k in text_lower for k in ["hardware", "fitting", "hinge", "handle"]):
        score += 0.15

    return min(1.0, round(score, 2))


def detect_category_and_material(item_title: str) -> tuple[str, str]:
    """Infers category and material from an item description."""
    text = item_title.lower()

    # Material
    if "brass" in text:
        material = "brass"
    elif "aluminium" in text or "aluminum" in text:
        material = "aluminium"
    elif "iron" in text or "steel" in text:
        material = "iron"
    elif "copper" in text:
        material = "copper"
    elif any(w in text for w in ["metal", "alloy"]):
        material = "metal_alloy"
    else:
        material = "unknown"

    # Category
    if any(w in text for w in ["trophy", "trophies", "memento", "award", "plaque", "shield"]):
        category = "trophy_memento"
    elif any(w in text for w in ["statue", "idol", "murti", "figurine", "sculpture"]):
        category = "statue_figure"
    elif any(w in text for w in ["vase", "planter", "lamp", "candle", "decor", "bowl"]):
        category = "home_decor"
    elif any(w in text for w in ["strip", "sheet", "ingot", "rod", "wire"]):
        category = "raw_material_metal"
    elif any(w in text for w in ["hinge", "handle", "knob", "lock", "fitting"]):
        category = "hardware_fitting"
    elif any(w in text for w in ["gift", "hamper", "souvenir"]):
        category = "gifting"
    else:
        category = "other"

    return category, material


def ingest_gem_json(filepath: Path) -> int:
    """Ingests and normalizes GeM bids from JSON."""
    if not filepath.exists():
        print(f"File not found: {filepath}")
        return 0

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    bids = data.get("results", [])
    ingested_count = 0

    print(f"\n📥 Ingesting {len(bids)} GeM bids from: {filepath.name}")

    for b in bids:
        bid_id = b.get("bid_id")
        if not bid_id or bid_id == "Unknown":
            continue

        items_str = b.get("items") or b.get("text") or "Government Procurement Tender"
        dept_name = b.get("department") or "Government of India"
        qty_str = b.get("quantity")
        end_date = b.get("end_date")
        link = b.get("link")

        # 1. Upsert Organization (Department)
        org_id = db.upsert_organization(
            name=dept_name,
            org_type="government_body",
            state="Central / Pan-India",
        )

        # 2. Score Intent
        intent_score = calculate_moradabad_intent_score(items_str + " " + dept_name)

        # 3. Upsert Intent Signal
        signal_id = db.upsert_intent_signal(
            source="gem",
            source_ref_id=bid_id,
            organization_id=org_id,
            title=f"GeM Tender: {items_str[:120]}",
            signal_type="tender_bid",
            signal_status="detected",
            intent_score=intent_score,
            closing_date=end_date,
            source_url=link,
            raw_payload=b,
        )

        # 4. Insert Signal Items
        category, material = detect_category_and_material(items_str)
        quantity = None
        if qty_str and qty_str.isdigit():
            quantity = int(qty_str)

        db.add_signal_item(
            signal_id=signal_id,
            item_title=items_str,
            category=category,
            material=material,
            quantity=quantity,
            unit="pieces",
        )

        ingested_count += 1
        print(f"  ✓ Normalized: [{bid_id}] Score: {intent_score} | {category.upper()} ({material})")

    return ingested_count


def ingest_mca_csv(filepath: Path) -> int:
    """
    Ingests and normalizes MCA company master data from a downloaded CSV.
    Expected standard MCA columns:
      - CIN, Company Name, ROC, Registration Date, Category, Class,
        Authorized Capital, Paidup Capital, State, Industrial Classification, Registered Address
    """
    if not filepath.exists():
        print(f"MCA CSV file not found: {filepath}")
        return 0

    print(f"\n📥 Ingesting MCA company records from: {filepath.name}")
    count = 0

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Map common variations of MCA column names
            cin = row.get("CIN") or row.get("cin") or row.get("Corporate Identification Number")
            name = row.get("Company Name") or row.get("company_name") or row.get("Company")
            if not name:
                continue

            state = row.get("State") or row.get("Company State") or row.get("state")
            ind_class = row.get("Company Industrial Classification") or row.get("Industrial Classification")
            auth_cap = row.get("Authorized Capital") or row.get("authorized_capital")
            paid_cap = row.get("Paidup Capital") or row.get("paid_up_capital")
            incorp_date = row.get("Date of Incorporation") or row.get("Registration Date")
            address = row.get("Registered Address") or row.get("Address")

            # Clean capitals
            def clean_num(val):
                if not val:
                    return None
                try:
                    return float(re.sub(r"[^\d.]", "", str(val)))
                except ValueError:
                    return None

            org_id = db.upsert_organization(
                name=name,
                org_type="private_limited",
                cin=cin,
                state=state,
                industrial_classification=ind_class,
                address=address,
                incorporation_date=incorp_date,
                authorized_capital=clean_num(auth_cap),
                paid_up_capital=clean_num(paid_cap),
            )

            # Intent scoring for newly incorporated companies
            score = 0.3
            text_context = f"{name} {ind_class or ''}"
            if any(k in text_context.lower() for k in ["gift", "decor", "handicraft", "brass", "metal", "interior"]):
                score = 0.85

            # Upsert incorporation as an intent signal
            ref_id = cin if cin else f"MCA_{name}_{incorp_date}"
            db.upsert_intent_signal(
                source="mca",
                source_ref_id=ref_id,
                organization_id=org_id,
                title=f"New Incorporation: {name}",
                signal_type="new_incorporation",
                signal_status="detected",
                intent_score=score,
                published_date=incorp_date,
                raw_payload=row,
            )
            count += 1

    print(f"✅ Ingested {count} MCA company records.")
    return count


if __name__ == "__main__":
    db.init_db()

    # Ingest today's captured Playwright bids
    playwright_file = DATA_DIR / "gem_playwright_bids.json"
    if playwright_file.exists():
        ingest_gem_json(playwright_file)

    print("\n" + "=" * 60)
    print("📊 CURRENT NORMALIZED DATABASE STATS:")
    print("=" * 60)
    for table, count in db.get_database_stats().items():
        print(f"  {table:25s}: {count} records")

    print("\n🌟 Top Extracted Intent Signals:")
    for lead in db.get_top_signals(5):
        print(f"  [{lead['source'].upper()}] {lead['source_ref_id']} (Score: {lead['intent_score']})")
        print(f"     Buyer: {lead['organization_name']}")
        print(f"     Demand: {lead['items_summary']}")
        print(f"     Deadline: {lead['closing_date']}")
        print()
