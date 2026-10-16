#!/usr/bin/env python3
"""
Universal Database Manager for Indian Business & Procurement Intelligence.
Handles SQLite operations for:
  - organizations (Companies, LLPs, Ministries, PSUs, MSMEs)
  - directors_officers (Company Directors, DIN, Signatories)
  - tenders (GeM, CPPP, and State Procurement Bids)
  - tender_items (Granular products and services demanded)
  - industrial_plants (Manufacturing units, factories, industrial areas)
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


def init_db(drop_existing: bool = False):
    """Initializes or resets SQLite database tables from schema.sql."""
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found at {SCHEMA_PATH}")

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with get_db_connection() as conn:
        if drop_existing:
            tables = ["tender_items", "tenders", "directors_officers", "industrial_plants", "organizations"]
            for t in tables:
                conn.execute(f"DROP TABLE IF EXISTS {t};")
            conn.commit()

        conn.executescript(schema_sql)
        conn.commit()

    print(f"✅ Database initialized at: {DB_PATH}")


# -----------------------------------------------------------------------------
# 1. Organizations (Companies, Ministries, MSMEs)
# -----------------------------------------------------------------------------
def upsert_organization(
    name: str,
    entity_type: str = "other",
    cin: Optional[str] = None,
    gstin: Optional[str] = None,
    pan: Optional[str] = None,
    udyam_number: Optional[str] = None,
    nic_code: Optional[str] = None,
    industrial_classification: Optional[str] = None,
    business_activity_description: Optional[str] = None,
    registered_address: Optional[str] = None,
    city: Optional[str] = None,
    district: Optional[str] = None,
    state: Optional[str] = None,
    pincode: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    website: Optional[str] = None,
    incorporation_date: Optional[str] = None,
    authorized_capital: Optional[float] = None,
    paid_up_capital: Optional[float] = None,
    company_status: str = "Active",
    roc_code: Optional[str] = None,
    source_origin: str = "unknown",
    raw_metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Inserts or finds an existing organization based on CIN, GSTIN, Udyam, or Name.
    Returns the organization ID.
    """
    name_clean = name.strip()
    raw_json = json.dumps(raw_metadata) if raw_metadata else None

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Check existing by unique identifiers
        if cin:
            cursor.execute("SELECT id FROM organizations WHERE cin = ?", (cin.strip(),))
            row = cursor.fetchone()
            if row:
                return row["id"]

        if gstin:
            cursor.execute("SELECT id FROM organizations WHERE gstin = ?", (gstin.strip(),))
            row = cursor.fetchone()
            if row:
                return row["id"]

        if udyam_number:
            cursor.execute("SELECT id FROM organizations WHERE udyam_number = ?", (udyam_number.strip(),))
            row = cursor.fetchone()
            if row:
                return row["id"]

        # Fallback to normalized name
        cursor.execute("SELECT id FROM organizations WHERE LOWER(name) = LOWER(?)", (name_clean,))
        row = cursor.fetchone()
        if row:
            return row["id"]

        # Insert new organization
        cursor.execute(
            """
            INSERT INTO organizations (
                name, entity_type, cin, gstin, pan, udyam_number,
                nic_code, industrial_classification, business_activity_description,
                registered_address, city, district, state, pincode,
                email, phone, website,
                incorporation_date, authorized_capital, paid_up_capital,
                company_status, roc_code, source_origin, raw_metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name_clean, entity_type, cin, gstin, pan, udyam_number,
                nic_code, industrial_classification, business_activity_description,
                registered_address, city, district, state, pincode,
                email, phone, website,
                incorporation_date, authorized_capital, paid_up_capital,
                company_status, roc_code, source_origin, raw_json
            ),
        )
        conn.commit()
        return cursor.lastrowid


# -----------------------------------------------------------------------------
# 2. Directors & Officers
# -----------------------------------------------------------------------------
def add_director_officer(
    organization_id: int,
    name: str,
    designation: Optional[str] = None,
    din: Optional[str] = None,
    pan: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    appointment_date: Optional[str] = None,
    is_active: int = 1,
) -> int:
    """Adds a director/officer to an organization."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO directors_officers (
                organization_id, name, designation, din, pan, phone, email,
                appointment_date, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (organization_id, name.strip(), designation, din, pan, phone, email, appointment_date, is_active),
        )
        conn.commit()
        return cursor.lastrowid


# -----------------------------------------------------------------------------
# 3. Tenders & Procurement Bids
# -----------------------------------------------------------------------------
def upsert_tender(
    source: str,
    bid_number: str,
    title: str,
    organization_id: Optional[int] = None,
    description: Optional[str] = None,
    bid_type: str = "goods",
    estimated_value: Optional[float] = None,
    currency: str = "INR",
    publishing_date: Optional[str] = None,
    closing_date: Optional[str] = None,
    opening_date: Optional[str] = None,
    status: str = "active",
    consignee_location: Optional[str] = None,
    document_url: Optional[str] = None,
    raw_payload: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Inserts a new tender or updates an existing one matching (source, bid_number).
    Returns the tender ID.
    """
    payload_json = json.dumps(raw_payload) if raw_payload else None

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tenders (
                organization_id, source, bid_number, title, description,
                bid_type, estimated_value, currency,
                publishing_date, closing_date, opening_date, status,
                consignee_location, document_url, raw_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, bid_number) DO UPDATE SET
                title = excluded.title,
                status = excluded.status,
                closing_date = COALESCE(excluded.closing_date, tenders.closing_date),
                document_url = COALESCE(excluded.document_url, tenders.document_url),
                raw_payload = COALESCE(excluded.raw_payload, tenders.raw_payload),
                updated_at = CURRENT_TIMESTAMP
            RETURNING id;
            """,
            (
                organization_id, source, bid_number.strip(), title.strip(), description,
                bid_type, estimated_value, currency,
                publishing_date, closing_date, opening_date, status,
                consignee_location, document_url, payload_json
            ),
        )
        row = cursor.fetchone()
        conn.commit()
        return row["id"]


# -----------------------------------------------------------------------------
# 4. Tender Items
# -----------------------------------------------------------------------------
def add_tender_item(
    tender_id: int,
    item_name: str,
    item_category: Optional[str] = None,
    specifications: Optional[str] = None,
    quantity: Optional[float] = None,
    unit: str = "units",
    estimated_unit_price: Optional[float] = None,
    total_estimated_value: Optional[float] = None,
    raw_item_payload: Optional[Dict[str, Any]] = None,
) -> int:
    """Inserts a granular product/line-item requested in a tender."""
    raw_json = json.dumps(raw_item_payload) if raw_item_payload else None

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tender_items (
                tender_id, item_name, item_category, specifications,
                quantity, unit, estimated_unit_price, total_estimated_value, raw_item_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tender_id, item_name.strip(), item_category, specifications,
                quantity, unit, estimated_unit_price, total_estimated_value, raw_json
            ),
        )
        conn.commit()
        return cursor.lastrowid


# -----------------------------------------------------------------------------
# 5. Industrial Plants & Manufacturing Units
# -----------------------------------------------------------------------------
def add_industrial_plant(
    unit_name: str,
    organization_id: Optional[int] = None,
    plant_type: str = "manufacturing",
    enterprise_category: str = "unclassified",
    address: Optional[str] = None,
    industrial_area: Optional[str] = None,
    district: Optional[str] = None,
    state: Optional[str] = None,
    pincode: Optional[str] = None,
    major_activity: Optional[str] = None,
    nic_code: Optional[str] = None,
    investment_in_machinery_lakhs: Optional[float] = None,
    annual_turnover_lakhs: Optional[float] = None,
    date_of_commencement: Optional[str] = None,
    raw_payload: Optional[Dict[str, Any]] = None,
) -> int:
    """Inserts a physical factory / manufacturing plant location."""
    raw_json = json.dumps(raw_payload) if raw_payload else None

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO industrial_plants (
                organization_id, unit_name, plant_type, enterprise_category,
                address, industrial_area, district, state, pincode,
                major_activity, nic_code, investment_in_machinery_lakhs,
                annual_turnover_lakhs, date_of_commencement, raw_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id, unit_name.strip(), plant_type, enterprise_category,
                address, industrial_area, district, state, pincode,
                major_activity, nic_code, investment_in_machinery_lakhs,
                annual_turnover_lakhs, date_of_commencement, raw_json
            ),
        )
        conn.commit()
        return cursor.lastrowid


# -----------------------------------------------------------------------------
# 6. Global Queries & Statistics
# -----------------------------------------------------------------------------
def get_database_stats() -> Dict[str, int]:
    """Returns row counts across all raw tables."""
    tables = ["organizations", "directors_officers", "tenders", "tender_items", "industrial_plants"]
    stats = {}
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for t in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM {t}")
                stats[t] = cursor.fetchone()["cnt"]
            except sqlite3.OperationalError:
                stats[t] = 0
    return stats


def get_latest_tenders(limit: int = 10, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches latest tenders with issuing organization and item details."""
    query = """
    SELECT 
        t.id,
        t.source,
        t.bid_number,
        t.title,
        t.status,
        t.closing_date,
        t.document_url,
        o.name AS issuing_organization,
        o.state AS org_state,
        COUNT(ti.id) AS item_count,
        GROUP_CONCAT(ti.item_name, ' | ') AS items_summary
    FROM tenders t
    LEFT JOIN organizations o ON t.organization_id = o.id
    LEFT JOIN tender_items ti ON t.id = ti.tender_id
    WHERE (? IS NULL OR ti.item_category = ?)
    GROUP BY t.id
    ORDER BY t.created_at DESC
    LIMIT ?;
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (category, category, limit))
        return [dict(row) for row in cursor.fetchall()]


if __name__ == "__main__":
    init_db(drop_existing=True)
    print("Database statistics:", get_database_stats())
