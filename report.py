#!/usr/bin/env python3
"""
Raw Business & Procurement Intelligence Reporter.
Queries data/pipeline.db to display:
  - Total records across all 5 raw core entities
  - Active Tenders across departments & sectors
  - Organizations & Ministries Directory
  - Industrial Units & Physical Plant Footprint
"""

import sqlite3
from datetime import datetime
from pathlib import Path

import db

DB_PATH = Path(__file__).parent / "data" / "pipeline.db"


def print_banner(title: str):
    print("\n" + "=" * 78)
    print(f"  {title}")
    print("=" * 78)


def generate_pipeline_report():
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}. Run 'python ingest.py' first.")
        return

    print_banner("🏛️  INDIAN BUSINESS & PROCUREMENT INTELLIGENCE — DATABASE REPORT")
    print(f"  Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Database:     {DB_PATH}")

    # 1. Summary Statistics
    stats = db.get_database_stats()
    print("\n📊 1. RAW ENTITY METRICS")
    print("-" * 55)
    print(f"  🏢 Organizations (Companies/Ministries) : {stats.get('organizations', 0):>5}")
    print(f"  👤 Directors & Key Officers (MCA DIN)   : {stats.get('directors_officers', 0):>5}")
    print(f"  📜 Public Tenders (GeM / CPPP)          : {stats.get('tenders', 0):>5}")
    print(f"  📦 Tender Products & Services Line Items : {stats.get('tender_items', 0):>5}")
    print(f"  🏭 Industrial Plants & MSME Units       : {stats.get('industrial_plants', 0):>5}")

    with db.get_db_connection() as conn:
        # 2. Active Tenders Across Sectors
        print_banner("📜 2. LATEST PUBLIC TENDERS (Active Procurement Bids)")
        tender_query = """
        SELECT 
            t.id,
            t.source,
            t.bid_number,
            t.closing_date,
            t.document_url,
            o.name AS organization_name,
            ti.item_name,
            ti.item_category,
            ti.quantity,
            ti.unit
        FROM tenders t
        JOIN organizations o ON t.organization_id = o.id
        LEFT JOIN tender_items ti ON t.id = ti.tender_id
        ORDER BY t.created_at DESC
        LIMIT 10;
        """
        tenders = conn.execute(tender_query).fetchall()

        if tenders:
            for idx, tender in enumerate(tenders, 1):
                qty = f"{tender['quantity']:,.0f} {tender['unit']}" if tender['quantity'] else "Unspecified"
                cat = (tender['item_category'] or 'general').upper()
                print(f"{idx:2d}. [{tender['source'].upper()}] {tender['bid_number']} | Sector: {cat}")
                print(f"    🏢 Issuing Body: {tender['organization_name']}")
                print(f"    📦 Demanded:     {tender['item_name']}")
                print(f"    📊 Quantity:     {qty}")
                print(f"    ⏰ Deadline:     {tender['closing_date'] or 'Open'}")
                if tender['document_url']:
                    print(f"    🔗 Link:         {tender['document_url']}")
                print()
        else:
            print("  No tenders recorded yet.")

        # 3. Category & Sector Distribution
        print_banner("📈 3. SECTOR & CATEGORY DISTRIBUTION (Tender Line Items)")
        cat_query = """
        SELECT item_category, COUNT(*) as count, SUM(COALESCE(quantity, 0)) as total_qty
        FROM tender_items
        GROUP BY item_category
        ORDER BY count DESC
        """
        breakdown = conn.execute(cat_query).fetchall()
        print(f"  {'Industrial Category':32s} | {'Tenders':8s} | {'Total Units Demanded':22s}")
        print("  " + "-" * 68)
        for row in breakdown:
            category_name = (row['item_category'] or 'unclassified').replace('_', ' ').title()
            print(f"  {category_name:32s} | {row['count']:>7}  | {row['total_qty']:>20,}")

        # 4. Registered Organizations Directory
        print_banner("🏢 4. REGISTERED ORGANIZATIONS IN DATABASE")
        org_query = """
        SELECT o.name, o.entity_type, o.source_origin, COUNT(t.id) as tender_count
        FROM organizations o
        LEFT JOIN tenders t ON o.id = t.organization_id
        GROUP BY o.id
        ORDER BY tender_count DESC
        """
        orgs = conn.execute(org_query).fetchall()
        for org in orgs:
            print(f"  • {org['name']} [{org['entity_type']}] (via {org['source_origin'].upper()}) — {org['tender_count']} tenders")

    print("\n" + "=" * 78)
    print("✨ Commands:")
    print("   Run GeM Scraper  : ./venv/bin/python playwright_gem.py")
    print("   Ingest & Normalize: ./venv/bin/python ingest.py")
    print("   View Report      : ./venv/bin/python report.py")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    generate_pipeline_report()
