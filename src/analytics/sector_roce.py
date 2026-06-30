"""
sector_roce.py — Sector-Relative ROCE Module
Nifty 100 Financial Intelligence Platform
Sprint 2 — Financial Ratio Engine

This module addresses a key real-world finance problem: the
standard ROCE formula is distorted for banks/NBFCs because their
"borrowings" are actually customer deposits, not traditional debt.

Instead of comparing Financials companies against the universal
Nifty 100 ROCE benchmark, this module computes a sector-relative
percentile rank so Financials are only compared against their
own peers.

Also performs a cross-validation of computed ROE against the
pre-computed roe_percentage field in companies.xlsx, flagging
anomalies for analyst review.

Usage:
    from src.analytics.sector_roce import run_sector_roce_analysis
    run_sector_roce_analysis()
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
NOTES_PATH = 'output/sector_roce_notes.csv'

# IMPORTANT: Do not assume max(year) is the most complete/recent year.
# Some companies report on non-standard fiscal year ends (e.g. Dec, Sep)
# which can create stray single-company "years" that are technically
# the maximum string value but have almost no company coverage.
# Always verify company coverage per year before picking a reference year.
ANALYSIS_YEAR = '2024-03'


# ── Find the Best Reference Year ──────────────────────────────────────────────

def find_best_reference_year(df):
    """
    Identifies the year with the highest company coverage to use
    as the reference "latest year" for cross-sectional comparisons.

    This avoids the bug of picking max(year) which may be a stray
    row from a single non-standard fiscal year-end company.

    Args:
        df: DataFrame with company_id and year columns

    Returns:
        str: The year string with maximum company coverage
    """
    year_counts = df.groupby('year')['company_id'].nunique().sort_values(
        ascending=False
    )
    best_year = year_counts.index[0]
    return best_year


# ── Sector-Relative ROCE ──────────────────────────────────────────────────────

def compute_sector_relative_roce(df):
    """
    Computes a sector-relative ROCE percentile score by ranking
    each company's ROCE against its own broad_sector peers within
    the same year, rather than the universal Nifty 100 range.

    This solves the bank/NBFC/Insurance distortion problem where
    the standard ROCE formula produces misleading values.

    Args:
        df: DataFrame with broad_sector, year, return_on_capital_pct

    Returns:
        DataFrame with roce_sector_percentile column added (0 to 1,
        higher = better ROCE relative to sector peers)
    """
    df = df.copy()
    df['roce_sector_percentile'] = df.groupby(
        ['broad_sector', 'year']
    )['return_on_capital_pct'].rank(pct=True).round(3)
    return df


# ── ROE Cross Validation ──────────────────────────────────────────────────────

def cross_validate_roe(ratios_df, companies_df, analysis_year, threshold=5.0):
    """
    Cross-checks computed ROE against the pre-computed roe_percentage
    field in companies.xlsx and flags anomalies above a threshold.

    Args:
        ratios_df:     Master ratios DataFrame
        companies_df:  Companies master DataFrame
        analysis_year: Year to use for comparison
        threshold:     Percentage point difference to flag as anomaly

    Returns:
        tuple: (full comparison DataFrame, anomalies-only DataFrame)
    """
    latest_roe = ratios_df[ratios_df['year'] == analysis_year][
        ['company_id', 'return_on_equity_pct']
    ].rename(columns={'return_on_equity_pct': 'computed_roe'})

    source_roe = companies_df[['id', 'roe_percentage']].rename(
        columns={'id': 'company_id', 'roe_percentage': 'source_roe'}
    )

    comparison = pd.merge(latest_roe, source_roe, on='company_id', how='inner')
    comparison['diff'] = abs(comparison['computed_roe'] - comparison['source_roe'])

    anomalies = comparison[comparison['diff'] > threshold].sort_values(
        'diff', ascending=False
    )

    return comparison, anomalies


# ── Identify Extreme Values ───────────────────────────────────────────────────

def find_extreme_equity_cases(ratios_df, analysis_year, roe_threshold=500):
    """
    Identifies companies with extreme ROE values (typically caused
    by very small equity capital + reserves base relative to profit).
    These need winsorisation before use in screener/health scoring.

    Args:
        ratios_df:     Master ratios DataFrame
        analysis_year: Year to check
        roe_threshold: ROE percentage above which is flagged extreme

    Returns:
        DataFrame: Companies with extreme ROE values
    """
    latest = ratios_df[ratios_df['year'] == analysis_year]
    extreme = latest[latest['return_on_equity_pct'] > roe_threshold][
        ['company_id', 'return_on_equity_pct', 'return_on_capital_pct']
    ].sort_values('return_on_equity_pct', ascending=False)

    return extreme


# ── Build Final Report ────────────────────────────────────────────────────────

def build_notes_report(financials_latest, non_financials_latest,
                        extreme_cases, anomalies):
    """
    Builds the final sector_roce_notes.csv report combining all findings.

    Args:
        financials_latest:     Financials sector rows for analysis year
        non_financials_latest: Non-Financials rows for analysis year
        extreme_cases:         Extreme equity base DataFrame
        anomalies:              ROE anomalies DataFrame

    Returns:
        DataFrame: Final notes report
    """
    notes = []

    # Sector summary
    notes.append({
        'category':       'Sector Summary',
        'company_id':     None,
        'computed_value': None,
        'source_value':   None,
        'diff':           None,
        'note': (
            f'Financials median ROCE: '
            f'{financials_latest["return_on_capital_pct"].median():.2f}% vs '
            f'Non-Financials: '
            f'{non_financials_latest["return_on_capital_pct"].median():.2f}%. '
            f'Financials median D/E: '
            f'{financials_latest["debt_to_equity"].median():.2f} vs '
            f'Non-Financials: '
            f'{non_financials_latest["debt_to_equity"].median():.2f}. '
            f'Standard ROCE/D-E distorted for banks/NBFCs due to deposits '
            f'counted as borrowings. Sector-relative percentile ranking '
            f'implemented instead.'
        )
    })

    # Extreme value findings
    for _, row in extreme_cases.iterrows():
        notes.append({
            'category':       'Extreme Value - Small Equity Base',
            'company_id':     row['company_id'],
            'computed_value': round(row['return_on_equity_pct'], 2),
            'source_value':   None,
            'diff':           None,
            'note': (
                f'{row["company_id"]} shows ROE of '
                f'{row["return_on_equity_pct"]:.0f}% due to very small '
                f'equity capital + reserves base relative to profit. '
                f'Mathematically correct but requires winsorisation '
                f'(cap at P10/P90) before use in Health Score or '
                f'screener ranking.'
            )
        })

    # ROE anomalies vs source
    for _, row in anomalies.iterrows():
        notes.append({
            'category':       'ROE Anomaly vs Source',
            'company_id':     row['company_id'],
            'computed_value': round(row['computed_roe'], 2),
            'source_value':   round(row['source_roe'], 2),
            'diff':           round(row['diff'], 2),
            'note': (
                f"Computed ROE ({row['computed_roe']:.2f}%) differs from "
                f"companies.xlsx source ({row['source_roe']:.2f}%) by "
                f"{row['diff']:.2f}pp. Flagged for analyst review."
            )
        })

    return pd.DataFrame(notes)


# ── Master Function ───────────────────────────────────────────────────────────

def run_sector_roce_analysis():
    """
    Master function — runs the full sector-relative ROCE analysis
    pipeline and saves the findings report.

    Pipeline:
        1. Load financial_ratios_computed table and sector mapping
        2. Find the best reference year (highest company coverage)
        3. Compare Financials vs Non-Financials ROCE and D/E
        4. Compute sector-relative ROCE percentile ranks
        5. Cross-validate computed ROE against source data
        6. Identify extreme equity base cases
        7. Save sector_roce_notes.csv

    Returns:
        DataFrame: The final notes report

    Example:
        from src.analytics.sector_roce import run_sector_roce_analysis
        notes_df = run_sector_roce_analysis()
    """
    from src.etl.loader import load_all_data

    data      = load_all_data()
    companies = data['companies']
    sectors   = data['sectors']

    conn = sqlite3.connect(DB_PATH)
    ratios = pd.read_sql_query(
        "SELECT * FROM financial_ratios_computed", conn
    )
    conn.close()

    # Merge sector info
    ratios_sector = ratios.merge(
        sectors[['company_id', 'broad_sector', 'sub_sector']],
        on='company_id', how='left'
    )

    # Find the best reference year (avoids stray-row bug)
    analysis_year = find_best_reference_year(ratios_sector)
    print(f"Using analysis year: {analysis_year}")

    latest = ratios_sector[ratios_sector['year'] == analysis_year]
    financials_latest     = latest[latest['broad_sector'] == 'Financials']
    non_financials_latest = latest[latest['broad_sector'] != 'Financials']

    print(f"\nROCE Comparison — Financials vs Non-Financials:")
    print(f"  Financials median ROCE:     "
          f"{financials_latest['return_on_capital_pct'].median():.2f}%")
    print(f"  Non-Financials median ROCE: "
          f"{non_financials_latest['return_on_capital_pct'].median():.2f}%")

    # Sector-relative ROCE
    ratios_sector = compute_sector_relative_roce(ratios_sector)

    # ROE cross-validation
    comparison, anomalies = cross_validate_roe(
        ratios_sector, companies, analysis_year
    )
    print(f"\nROE cross-validation: {len(comparison)} companies compared, "
          f"{len(anomalies)} anomalies found")

    # Extreme equity base cases
    extreme_cases = find_extreme_equity_cases(ratios_sector, analysis_year)
    print(f"Extreme equity base cases found: {len(extreme_cases)}")

    # Build and save report
    notes_df = build_notes_report(
        financials_latest, non_financials_latest, extreme_cases, anomalies
    )
    notes_df.to_csv(NOTES_PATH, index=False)

    print(f"\nsector_roce_notes.csv saved with {len(notes_df)} entries!")
    print(f"\nSummary by category:")
    print(notes_df['category'].value_counts().to_string())

    return notes_df


# ── Run directly for testing ──────────────────────────────────────────────────

if __name__ == "__main__":
    run_sector_roce_analysis()
