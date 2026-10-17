import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import DB_PATH, SCHEMA_PATH


class DatabaseManager:
    """Manages SQLite connection and operations for Indian Business Intelligence."""

    def __init__(self, db_path: Path = DB_PATH, schema_path: Path = SCHEMA_PATH):
        self.db_path = db_path
        self.schema_path = schema_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Returns SQLite connection with row_factory and foreign keys enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self, drop_existing: bool = False):
        """Initializes tables using schema.sql."""
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {self.schema_path}")

        with open(self.schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        with self.get_connection() as conn:
            if drop_existing:
                tables = ["tender_items", "tenders", "directors_officers", "industrial_plants", "organizations"]
                for t in tables:
                    conn.execute(f"DROP TABLE IF EXISTS {t};")
                conn.commit()
            conn.executescript(schema_sql)
            conn.commit()

    def get_stats(self) -> Dict[str, int]:
        """Returns row counts across primary tables."""
        tables = ["organizations", "directors_officers", "tenders", "tender_items", "industrial_plants"]
        stats = {}
        with self.get_connection() as conn:
            cur = conn.cursor()
            for t in tables:
                try:
                    cur.execute(f"SELECT COUNT(*) as cnt FROM {t}")
                    stats[t] = cur.fetchone()["cnt"]
                except sqlite3.OperationalError:
                    stats[t] = 0
        return stats
