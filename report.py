#!/usr/bin/env python3
"""
Pipeline Status & Lead Report.
Queries data/pipeline.db and prints a structured summary of:
  - Total normalized entities (Organizations, Signals, Items)
  - High-priority Buyer Intent Leads (sorted by score & deadline)
  - Demand distribution by material and category
"""

import sqlite3
from datetime import datetime
from pathlib import Path

import db

DB_PATH = Path(__file__).parent / "data" / "pipeline.db"


def print_banner(title: str):
    print("\n" + "=" * 75)
    print(f"  {title}")
    print("=" * 75)


def generate_pipeline_report():
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}. Run 'python ingest.py' first.")
        return

    print_banner("🏛️  MORADABAD B2B MATCHMAKING PIPELINE — DATABASE REPORT")
    print(f"  Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Database:     {DB_PATH}")

    # 1. Summary Statistics
    stats = db.get_database_stats()
    print("\n📊 1. DATABASE METRICS")
    print("-" * 55)
    print(f"  🏢 Organizations (Buyers/Depts)  : {stats.get('organizations', 0):>4}")
    print(f"  📡 Total Intent Signals (Bids)   : {stats.get('intent_signals', 0):>4}")
    print(f"  📦 Granular Line Items Demanded  : {stats.get('signal_items', 0):>4}")
    print(f"  📞 Completed Qualification Calls : {stats.get('qualification_calls', 0):>4}")

    with db.get_db_connection() as conn:
        # 2. High-Intent Leads Queue (Score >= 0.5)
        print_banner("🎯 2. HIGH-INTENT BUYER LEADS (Ready for Qualification)")
        high_intent_query = """
        SELECT 
            s.id,
            s.source,
            s.source_ref_id,
            s.intent_score,
            s.signal_status,
            s.closing_date,
            s.source_url,
            o.name AS buyer_name,
            o.org_type,
            i.item_title,
            i.category,
            i.material,
            i.quantity,
            i.unit
        FROM intent_signals s
        JOIN organizations o ON s.organization_id = o.id
        LEFT JOIN signal_items i ON s.id = i.signal_id
        WHERE s.intent_score >= 0.3
        ORDER BY s.intent_score DESC, s.closing_date ASC
        """
        leads = conn.execute(high_intent_query).fetchall()

        if leads:
            for idx, lead in enumerate(leads, 1):
                score_bar = "🟢" if lead["intent_score"] >= 0.7 else "🟡"
                qty = f"{lead['quantity']:,} {lead['unit']}" if lead['quantity'] else "N/A"
                print(f"{idx}. {score_bar} [{lead['source'].upper()}] {lead['source_ref_id']} | Fit Score: {lead['intent_score']}")
                print(f"   🏢 Buyer:       {lead['buyer_name']} ({lead['org_type']})")
                print(f"   📦 Demanded:    {lead['item_title']}")
                print(f"   🏷️  Category:    {lead['category'].upper()} | Material: {lead['material'].upper()} | Qty: {qty}")
                print(f"   ⏰ Deadline:    {lead['closing_date'] or 'Open'}")
                if lead['source_url']:
                    print(f"   🔗 Link:        {lead['source_url']}")
                print()
        else:
            print("  No high-intent leads recorded yet.")

        # 3. Demand Breakdown by Category & Material
        print_banner("📈 3. DEMAND BREAKDOWN")
        cat_query = """
        SELECT category, material, COUNT(*) as count, SUM(COALESCE(quantity, 0)) as total_qty
        FROM signal_items
        GROUP BY category, material
        ORDER BY count DESC
        """
        breakdown = conn.execute(cat_query).fetchall()
        print(f"  {'Category':22s} | {'Material':15s} | {'Tenders':8s} | {'Total Units Demanded':20s}")
        print("  " + "-" * 71)
        for row in breakdown:
            print(f"  {row['category']:22s} | {row['material']:15s} | {row['count']:>7}  | {row['total_qty']:>18,}")

        # 4. Registered Organizations
        print_banner("🏢 4. BUYER ORGANIZATIONS IN DATABASE")
        org_query = """
        SELECT o.name, o.org_type, o.state, COUNT(s.id) as signal_count
        FROM organizations o
        LEFT JOIN intent_signals s ON o.id = s.organization_id
        GROUP BY o.id
        ORDER BY signal_count DESC
        """
        orgs = conn.execute(org_query).fetchall()
        for org in orgs:
            print(f"  • {org['name']} ({org['org_type']}) — {org['signal_count']} active signals")

    print("\n" + "=" * 75)
    print("✨ To update data: run './venv/bin/python playwright_gem.py && ./venv/bin/python ingest.py'")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    generate_pipeline_report()

