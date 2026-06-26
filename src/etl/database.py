"""
database.py — SQLite Database Loading Module
Nifty 100 Financial Intelligence Platform
Sprint 1 — Data Foundation

This module takes all clean DataFrames from loader.py and loads
them into a SQLite database (nifty100.db). Also generates a
load_audit.csv report confirming row counts for all tables.

Usage:
    from src.etl.database import build_database
    build_database()
"""

import sqlite3
import pandas as pd
import os
import sys

# ── Path Configuration ────────────────────────────────────────────────────────

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(PROJECT_PATH)
os.chdir(PROJECT_PATH)

DB_PATH       = 'data/nifty100.db'
AUDIT_PATH    = 'output/load_audit.csv'

# ── Database Connection ───────────────────────────────────────────────────────

def get_connection():
    """
    Creates and returns a connection to the SQLite database.

    Returns:
        sqlite3.Connection: Active database connection
    """
    conn = sqlite3.connect(DB_PATH)
    return conn


# ── Table Loader ──────────────────────────────────────────────────────────────

def load_tables(data: dict, conn: sqlite3.Connection):
    """
    Loads all DataFrames into SQLite database tables.
    If a table already exists it will be replaced.

    Args:
        data: Dictionary of dataset name → clean DataFrame
        conn: Active SQLite connection
    """
    print("Loading tables into database...")

    for table_name, df in data.items():
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"  Loaded → {table_name:20s} ({len(df)} rows)")

    print("\nAll tables loaded successfully!")


# ── Audit Report ──────────────────────────────────────────────────────────────

def generate_audit(conn: sqlite3.Connection):
    """
    Generates a load_audit.csv report with row counts for all tables.
    This is a required Sprint 1 deliverable.

    Args:
        conn: Active SQLite connection

    Returns:
        DataFrame: Audit report with table name, row count, and status
    """
    cursor = conn.cursor()

    # Get all table names from the database
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    table_names = [row[0] for row in cursor.fetchall()]

    audit_rows = []
    for table_name in table_names:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        audit_rows.append({
            'table':  table_name,
            'rows':   row_count,
            'status': 'OK' if row_count > 0 else 'EMPTY'
        })

    audit_df = pd.DataFrame(audit_rows)
    audit_df.to_csv(AUDIT_PATH, index=False)

    print(f"\nload_audit.csv saved to {AUDIT_PATH}")
    print()
    print(audit_df.to_string(index=False))

    return audit_df


# ── Verify Tables ─────────────────────────────────────────────────────────────

def verify_tables(conn: sqlite3.Connection):
    """
    Prints all tables currently in the database.

    Args:
        conn: Active SQLite connection
    """
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    print("\nTables in nifty100.db:")
    for table in tables:
        print(f"  ✅ {table[0]}")


# ── Query Helper ──────────────────────────────────────────────────────────────

def run_query(query: str, conn: sqlite3.Connection):
    """
    Runs a SQL query and returns results as a DataFrame.
    Used by other modules to query the database.

    Args:
        query: SQL query string
        conn:  Active SQLite connection

    Returns:
        DataFrame: Query results
    """
    return pd.read_sql_query(query, conn)


# ── Master Builder ────────────────────────────────────────────────────────────

def build_database():
    """
    Master function — loads all data and builds the database.
    Runs the full pipeline:
        1. Load all clean DataFrames via loader.py
        2. Connect to SQLite
        3. Load all tables
        4. Verify tables exist
        5. Generate load_audit.csv

    Example:
        from src.etl.database import build_database
        build_database()
    """
    from src.etl.loader import load_all_data

    # Step 1 — Load clean data
    data = load_all_data()

    # Step 2 — Connect to database
    print(f"\nConnecting to database at {DB_PATH}...")
    conn = get_connection()
    print("Connected!")

    # Step 3 — Load all tables
    load_tables(data, conn)

    # Step 4 — Verify
    verify_tables(conn)

    # Step 5 — Audit report
    generate_audit(conn)

    # Step 6 — Close connection
    conn.close()
    print("\nDatabase connection closed.")
    print("Sprint 1 — Data Foundation Complete! ✅")


# ── Run directly for testing ──────────────────────────────────────────────────

if __name__ == "__main__":
    build_database()
