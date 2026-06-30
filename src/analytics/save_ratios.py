"""
save_ratios.py — Master KPI Integration Module
Nifty 100 Financial Intelligence Platform
Sprint 2 — Financial Ratio Engine

This module combines outputs from ratios.py, cagr.py and
cashflow_kpis.py into a single master financial_ratios table
and persists it to the SQLite database (nifty100.db).

This becomes the single source of truth for all downstream
modules: Screener, Health Score, Sector Analytics, Dashboard,
and PDF/Excel reports.

Usage:
    from src.analytics.save_ratios import build_financial_ratios_table
    master_df = build_financial_ratios_table()
"""

import pandas as pd
import numpy as np
import sqlite3
import os
import sys

# ── Path Configuration ────────────────────────────────────────────────────────

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(PROJECT_PATH)
os.chdir(PROJECT_PATH)

DB_PATH    = 'data/nifty100.db'
TABLE_NAME = 'financial_ratios_computed'

# ── Merge All KPI Sets ─────────────────────────────────────────────────────────

def merge_all_kpis(ratios_df, cagr_df, cashflow_df):
    """
    Merges profitability/leverage ratios, CAGR growth metrics and
    cash flow KPIs into a single master DataFrame.

    Note: ratios_df and cashflow_df are at (company_id, year) grain.
    cagr_df is at company_id grain only (CAGR is a single computed
    value per company, not per year) so it joins on company_id alone.

    Args:
        ratios_df:   Output of compute_all_ratios()
        cagr_df:     Output of compute_all_cagr()
        cashflow_df: Output of compute_all_cashflow_kpis()

    Returns:
        DataFrame: Master table with all KPIs merged
    """
    # Merge ratios with cash flow KPIs on company_id + year
    master = pd.merge(
        ratios_df,
        cashflow_df,
        on=['company_id', 'year'],
        how='outer'
    )

    # Merge CAGR (company-level) onto every year for that company
    master = pd.merge(
        master,
        cagr_df,
        on='company_id',
        how='left'
    )

    # Sort for readability and consistency
    master = master.sort_values(['company_id', 'year']).reset_index(drop=True)

    return master


# ── Validation ─────────────────────────────────────────────────────────────────

def validate_master_table(master):
    """
    Runs basic sanity checks on the merged master table.

    Args:
        master: Merged master DataFrame

    Returns:
        dict: Validation summary
    """
    dupes = master[master.duplicated(subset=['company_id', 'year'])]

    summary = {
        'total_rows':        len(master),
        'unique_companies':  master['company_id'].nunique(),
        'duplicate_rows':    len(dupes),
        'year_min':          master['year'].min(),
        'year_max':          master['year'].max(),
        'total_columns':     len(master.columns),
    }

    print("Master Table Validation:")
    print(f"  Total rows:        {summary['total_rows']}")
    print(f"  Unique companies:  {summary['unique_companies']}")
    print(f"  Duplicate rows:    {summary['duplicate_rows']}")
    print(f"  Year range:        {summary['year_min']} to {summary['year_max']}")
    print(f"  Total columns:     {summary['total_columns']}")

    return summary


# ── Save to Database ──────────────────────────────────────────────────────────

def save_to_database(master, table_name=TABLE_NAME):
    """
    Saves the master financial ratios table to SQLite database.

    Args:
        master:     Master DataFrame to save
        table_name: Name of the table in the database

    Returns:
        int: Number of rows saved
    """
    conn = sqlite3.connect(DB_PATH)

    master.to_sql(table_name, conn, if_exists='replace', index=False)

    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    row_count = cursor.fetchone()[0]

    print(f"\nSaved to database as '{table_name}' table!")
    print(f"Row count in database: {row_count}")

    conn.close()
    return row_count


# ── Query Helper ──────────────────────────────────────────────────────────────

def query_company_ratios(company_id, table_name=TABLE_NAME):
    """
    Convenience function to query all ratios for a single company.

    Args:
        company_id: NSE ticker e.g. 'TCS'
        table_name: Name of the table to query

    Returns:
        DataFrame: All KPI rows for the given company, sorted by year
    """
    conn = sqlite3.connect(DB_PATH)

    query = f"""
        SELECT *
        FROM {table_name}
        WHERE company_id = ?
        ORDER BY year DESC
    """

    result = pd.read_sql_query(query, conn, params=(company_id,))
    conn.close()

    return result


# ── Master Builder ────────────────────────────────────────────────────────────

def build_financial_ratios_table():
    """
    Master function — computes all KPI sets, merges them, validates,
    and saves the final financial_ratios table to the database.

    Runs the full pipeline:
        1. Compute profitability/leverage/efficiency ratios
        2. Compute CAGR growth ratios
        3. Compute cash flow KPIs
        4. Merge all three into one master table
        5. Validate the merged table
        6. Save to SQLite database

    Returns:
        DataFrame: The final merged and saved master table

    Example:
        from src.analytics.save_ratios import build_financial_ratios_table
        master_df = build_financial_ratios_table()
    """
    from src.analytics.ratios import compute_all_ratios
    from src.analytics.cagr import compute_all_cagr
    from src.analytics.cashflow_kpis import compute_all_cashflow_kpis

    print("=" * 50)
    print("Building Master Financial Ratios Table")
    print("=" * 50)

    print("\nStep 1/3 — Computing profitability/leverage/efficiency ratios...")
    ratios_df = compute_all_ratios()

    print("\nStep 2/3 — Computing CAGR growth ratios...")
    cagr_df = compute_all_cagr()

    print("\nStep 3/3 — Computing cash flow KPIs...")
    cashflow_df = compute_all_cashflow_kpis()

    print("\nMerging all KPI sets...")
    master = merge_all_kpis(ratios_df, cagr_df, cashflow_df)

    print()
    validate_master_table(master)

    save_to_database(master)

    print("\n" + "=" * 50)
    print("Sprint 2 Day 5 Complete — financial_ratios table ready!")
    print("=" * 50)

    return master


# ── Run directly for testing ──────────────────────────────────────────────────

if __name__ == "__main__":
    master_df = build_financial_ratios_table()

    print("\nSample — TCS last 5 years:")
    tcs = query_company_ratios('TCS').head(5)
    cols = ['company_id', 'year', 'return_on_equity_pct',
            'debt_to_equity', 'free_cash_flow_cr',
            'sales_cagr_5yr', 'cf_label']
    print(tcs[cols].to_string(index=False))
