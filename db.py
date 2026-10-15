#!/usr/bin/env python3
"""
Database manager for the Moradabad B2B Matchmaking Pipeline.
Handles SQLite connection, schema initialization, and transactional upserts
for Organizations, Officers, Intent Signals, and Line Items.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_DIR = Path(__file__).parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "pipeline.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_db_connection() -> sqlite3.Connection:
    """Returns an active SQLite connection with row_factory and foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Initializes SQLite database tables from schema.sql."""
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found at {SCHEMA_PATH}")

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with get_db_connection() as conn:
        conn.executescript(schema_sql)
        conn.commit()

    print(f"✅ Database initialized at: {DB_PATH}")


# -----------------------------------------------------------------------------
# 1. Organizations Upsert
# -----------------------------------------------------------------------------
def upsert_organization(
    name: str,
    org_type: str = "other",
    cin: Optional[str] = None,
    gst_number: Optional[str] = None,
    pan: Optional[str] = None,
    udyam_reg_number: Optional[str] = None,
    industrial_classification: Optional[str] = None,
    business_activity: Optional[str] = None,
    address: Optional[str] = None,
    city: Optional[str] = None,
    district: Optional[str] = None,
    state: Optional[str] = None,
    pincode: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    website: Optional[str] = None,
    incorporation_date: Optional[str] = None,
    authorized_capital: Optional[float] = None,
    paid_up_capital: Optional[float] = None,
    company_status: str = "Active",
) -> int:
    """
    Inserts or finds an existing organization based on CIN, GSTIN, or name.
    Returns the organization ID.
    """
    name_clean = name.strip()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Check by CIN first (if available)
        if cin:
            cursor.execute("SELECT id FROM organizations WHERE cin = ?", (cin,))
            row = cursor.fetchone()
            if row:
                return row["id"]

        # Check by GSTIN (if available)
        if gst_number:
            cursor.execute("SELECT id FROM organizations WHERE gst_number = ?", (gst_number,))
            row = cursor.fetchone()
            if row:
                return row["id"]

        # Check by normalized name
        cursor.execute("SELECT id FROM organizations WHERE LOWER(name) = LOWER(?)", (name_clean,))
        row = cursor.fetchone()
        if row:
            return row["id"]

        # Insert new organization
        cursor.execute(
            """
            INSERT INTO organizations (
                name, org_type, cin, gst_number, pan, udyam_reg_number,
                industrial_classification, business_activity, address,
                city, district, state, pincode, phone, email, website,
                incorporation_date, authorized_capital, paid_up_capital, company_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name_clean, org_type, cin, gst_number, pan, udyam_reg_number,
                industrial_classification, business_activity, address,
                city, district, state, pincode, phone, email, website,
                incorporation_date, authorized_capital, paid_up_capital, company_status
            ),
        )
        conn.commit()
        return cursor.lastrowid


# -----------------------------------------------------------------------------
# 2. Organization Officers (Directors, Procurement Managers)
# -----------------------------------------------------------------------------
def add_organization_officer(
    organization_id: int,
    name: str,
    designation: Optional[str] = None,
    din: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
) -> int:
    """Adds a director/officer to an organization."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO organization_officers (
                organization_id, name, designation, din, phone, email
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (organization_id, name.strip(), designation, din, phone, email),
        )
        conn.commit()
        return cursor.lastrowid


# -----------------------------------------------------------------------------
# 3. Intent Signals Upsert
# -----------------------------------------------------------------------------
def upsert_intent_signal(
    source: str,
    source_ref_id: str,
    organization_id: Optional[int] = None,
    title: Optional[str] = None,
    signal_type: str = "tender_bid",
    signal_status: str = "detected",
    intent_score: float = 0.5,
    published_date: Optional[str] = None,
    closing_date: Optional[str] = None,
    source_url: Optional[str] = None,
    raw_payload: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Inserts a new intent signal or updates an existing one matching (source, source_ref_id).
    Returns the signal ID.
    """
    payload_json = json.dumps(raw_payload) if raw_payload else None

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO intent_signals (
                organization_id, source, source_ref_id, title,
                signal_type, signal_status, intent_score,
                published_date, closing_date, source_url, raw_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, source_ref_id) DO UPDATE SET
                signal_status = excluded.signal_status,
                intent_score = excluded.intent_score,
                closing_date = COALESCE(excluded.closing_date, intent_signals.closing_date),
                source_url = COALESCE(excluded.source_url, intent_signals.source_url),
                raw_payload = COALESCE(excluded.raw_payload, intent_signals.raw_payload)
            RETURNING id;
            """,
            (
                organization_id, source, source_ref_id, title,
                signal_type, signal_status, intent_score,
                published_date, closing_date, source_url, payload_json
            ),
        )
        row = cursor.fetchone()
        conn.commit()
        return row["id"]


# -----------------------------------------------------------------------------
# 4. Signal Items (Granular Demand Items)
# -----------------------------------------------------------------------------
def add_signal_item(
    signal_id: int,
    item_title: str,
    category: str = "other",
    material: str = "unknown",
    quantity: Optional[int] = None,
    unit: str = "pieces",
    estimated_budget: Optional[float] = None,
    specifications: Optional[str] = None,
) -> int:
    """Adds a granular line-item to an intent signal."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO signal_items (
                signal_id, item_title, category, material,
                quantity, unit, estimated_budget, specifications
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal_id, item_title.strip(), category, material,
                quantity, unit, estimated_budget, specifications
            ),
        )
        conn.commit()
        return cursor.lastrowid


# -----------------------------------------------------------------------------
# 5. Queries & Stats
# -----------------------------------------------------------------------------
def get_database_stats() -> Dict[str, int]:
    """Returns total record counts across all core tables."""
    tables = ["organizations", "organization_officers", "intent_signals", "signal_items", "qualification_calls"]
    stats = {}
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for t in tables:
            cursor.execute(f"SELECT COUNT(*) as cnt FROM {t}")
            stats[t] = cursor.fetchone()["cnt"]
    return stats


def get_top_signals(limit: int = 10) -> List[Dict[str, Any]]:
    """Fetches top intent signals with organization and item summaries."""
    query = """
    SELECT 
        s.id,
        s.source,
        s.source_ref_id,
        s.title,
        s.signal_status,
        s.intent_score,
        s.closing_date,
        s.source_url,
        o.name AS organization_name,
        o.state AS org_state,
        COUNT(i.id) AS item_count,
        GROUP_CONCAT(i.item_title, ' | ') AS items_summary
    FROM intent_signals s
    LEFT JOIN organizations o ON s.organization_id = o.id
    LEFT JOIN signal_items i ON s.id = i.signal_id
    GROUP BY s.id
    ORDER BY s.intent_score DESC, s.detected_at DESC
    LIMIT ?
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (limit,))
        return [dict(row) for row in cursor.fetchall()]


if __name__ == "__main__":
    init_db()
    print("Database statistics:", get_database_stats())
