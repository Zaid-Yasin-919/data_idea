#!/usr/bin/env python3
"""CLI interface for Indian Business & Procurement Intelligence Pipeline."""

import argparse
from src.pipeline.db import DatabaseManager


def main():
    parser = argparse.ArgumentParser(description="Procurement & Business Intelligence Pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: db
    db_parser = subparsers.add_parser("db", help="Database management")
    db_parser.add_argument("--init", action="store_true", help="Initialize database schema")
    db_parser.add_argument("--stats", action="store_true", help="Display table statistics")

    args = parser.parse_args()
    db = DatabaseManager()

    if args.command == "db":
        if args.init:
            db.init_db()
            print("Database initialized successfully.")
        if args.stats:
            stats = db.get_stats()
            print("Database Statistics:")
            for table, count in stats.items():
                print(f"  {table}: {count} rows")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

