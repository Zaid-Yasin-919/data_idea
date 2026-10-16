#!/usr/bin/env python3
"""
Raw Data Ingestion & Normalization Engine.

Universal ETL pipeline:
  1. GeM & CPPP Tenders -> organizations (ministries/PSUs), tenders, tender_items
  2. MCA Corporate Data -> organizations (companies/LLPs), directors_officers
  3. MSME / Factory Data -> industrial_plants, organizations

Sector-Agnostic: Stores full raw payloads and standard classifications.
"""

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import db

DATA_DIR = Path(__file__).parent / "data"


def infer_broad_category(text: str) -> str:
    """Classifies a product/tender into a broad economic/industrial category."""
    t = text.lower()
    if any(k in t for k in ["computer", "laptop", "server", "software", "printer", "network", "cctv", "electronic", "ups"]):
        return "it_electronics"
    elif any(k in t for k in ["vehicle", "car", "bus", "truck", "ambulance", "tyre", "automobile", "dumper"]):
        return "automotive_transport"
    elif any(k in t for k in ["medicine", "medical", "hospital", "pharma", "surgical", "health", "elisa", "drug"]):
        return "medical_healthcare"
    elif any(k in t for k in ["pipe", "valve", "pump", "motor", "casting", "sheet", "strip", "rod", "steel", "iron", "brass", "metal"]):
        return "metals_machinery"
    elif any(k in t for k in ["civil", "construction", "cement", "road", "building", "repair", "painting", "tarpaulin"]):
        return "construction_works"
    elif any(k in t for k in ["chair", "table", "furniture", "almirah", "sofa", "desk"]):
        return "furniture_fixtures"
    elif any(k in t for k in ["paper", "pen", "stationery", "copier", "office", "toner"]):
        return "office_supplies"
    elif any(k in t for k in ["trophy", "memento", "gift", "handicraft", "award", "plaque", "shield"]):
        return "gifting_handicrafts"
    elif any(k in t for k in ["uniform", "cloth", "textile", "leather", "shoes", "boot", "fabric"]):
        return "textiles_apparel"
    elif any(k in t for k in ["security", "manpower", "cleaning", "canteen", "catering", "housekeeping"]):
        return "facility_services"
    else:
        return "general_procurement"


def ingest_gem_json(filepath: Path) -> int:
    """Ingests raw GeM tender JSON dumps into normalized tables."""
    if not filepath.exists():
        print(f"File not found: {filepath}")
        return 0

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    bids = data.get("results", [])
    ingested_count = 0

    print(f"\n📥 Ingesting {len(bids)} tenders from: {filepath.name}")

    for b in bids:
        bid_id = b.get("bid_id")
        if not bid_id or bid_id == "Unknown":
            continue

        item_desc = b.get("items") or b.get("text") or "Public Procurement Tender"
        dept_name = b.get("department") or "Government of India"
        qty_str = b.get("quantity")
        end_date = b.get("end_date")
        link = b.get("link")

        # 1. Upsert Issuing Organization
        org_id = db.upsert_organization(
            name=dept_name,
            entity_type="government_body",
            source_origin="gem",
        )

        # 2. Upsert Tender
        tender_id = db.upsert_tender(
            source="gem",
            bid_number=bid_id,
            title=item_desc[:200],
            organization_id=org_id,
            closing_date=end_date,
            document_url=link,
            raw_payload=b,
        )

        # 3. Add Tender Line-Item
        category = infer_broad_category(item_desc)
        quantity = None
        if qty_str:
            clean_digits = re.sub(r"[^\d]", "", str(qty_str))
            if clean_digits:
                quantity = float(clean_digits)

        db.add_tender_item(
            tender_id=tender_id,
            item_name=item_desc,
            item_category=category,
            quantity=quantity,
            unit="units",
            raw_item_payload=b,
        )

        ingested_count += 1
        print(f"  ✓ Tender: [{bid_id}] Category: {category:20s} | Org: {dept_name}")

    return ingested_count


def ingest_mca_csv(filepath: Path) -> int:
    """
    Ingests official MCA corporate master CSV exports into the database.
    Handles standard MCA headers: CIN, Company Name, RoC, Class,
    Date of Incorporation, Authorized Capital, Paid-up Capital, State,
    Industrial Classification, Address.
    """
    if not filepath.exists():
        print(f"MCA CSV file not found: {filepath}")
        return 0

    print(f"\n📥 Ingesting MCA company master records from: {filepath.name}")
    count = 0

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
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
            roc = row.get("RoC") or row.get("ROC")

            def clean_num(val):
                if not val:
                    return None
                try:
                    return float(re.sub(r"[^\d.]", "", str(val)))
                except ValueError:
                    return None

            db.upsert_organization(
                name=name,
                entity_type="private_limited",
                cin=cin,
                state=state,
                industrial_classification=ind_class,
                registered_address=address,
                incorporation_date=incorp_date,
                authorized_capital=clean_num(auth_cap),
                paid_up_capital=clean_num(paid_cap),
                roc_code=roc,
                source_origin="mca",
                raw_metadata=row,
            )
            count += 1

    print(f"✅ Ingested {count} MCA company records.")
    return count


def ingest_udyam_csv(filepath: Path) -> int:
    """
    Ingests Udyam / MSME plant & industrial unit records.
    Maps physical plant footprint, enterprise size, district, and machinery investment.
    """
    if not filepath.exists():
        print(f"Udyam CSV not found: {filepath}")
        return 0

    print(f"\n📥 Ingesting Udyam industrial unit records from: {filepath.name}")
    count = 0

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            unit_name = row.get("Enterprise Name") or row.get("Unit Name") or row.get("Name")
            udyam_no = row.get("Udyam Registration Number") or row.get("URN")
            if not unit_name:
                continue

            ent_type = (row.get("Enterprise Type") or "unclassified").lower()
            state = row.get("State")
            district = row.get("District")
            activity = row.get("Major Activity") or row.get("Activity")
            nic = row.get("NIC Code")

            org_id = db.upsert_organization(
                name=unit_name,
                entity_type="msme_unit",
                udyam_number=udyam_no,
                state=state,
                district=district,
                industrial_classification=activity,
                source_origin="udyam",
                raw_metadata=row,
            )

            db.add_industrial_plant(
                unit_name=unit_name,
                organization_id=org_id,
                enterprise_category=ent_type if ent_type in ['micro', 'small', 'medium', 'large'] else 'unclassified',
                state=state,
                district=district,
                major_activity=activity,
                nic_code=nic,
                raw_payload=row,
            )
            count += 1

    print(f"✅ Ingested {count} industrial units.")
    return count


if __name__ == "__main__":
    db.init_db(drop_existing=True)

    # Ingest existing GeM tenders
    playwright_file = DATA_DIR / "gem_playwright_bids.json"
    if playwright_file.exists():
        ingest_gem_json(playwright_file)

    print("\n" + "=" * 65)
    print("📊 RAW DATABASE STATUS:")
    print("=" * 65)
    for table, count in db.get_database_stats().items():
        print(f"  {table:25s}: {count:>4} records")
