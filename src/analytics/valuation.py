"""
valuation.py — Valuation Analysis Module
Nifty 100 Financial Intelligence Platform
Sprint 4 — Valuation & Investment Intelligence

Computes valuation multiples (P/E, P/B, EV/EBITDA, FCF Yield)
and generates overvaluation/undervaluation flags for all 92 companies.

Metrics Computed:
    - FCF Yield: Free Cash Flow / Market Cap (%)
    - Sector Median P/E: Median P/E within each sector
    - P/E vs Sector: Relative valuation flag (Caution/Discount/Fair)
    - Valuation Bands: Classification by FCF yield

Output:
    - output/valuation_summary.xlsx: All 92 companies with multiples
    - output/valuation_flags.csv: Flagged companies only

Usage:
    from src.analytics.valuation import run_valuation_analysis
    val_df = run_valuation_analysis()
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

DB_PATH            = 'data/nifty100.db'
ANALYSIS_YEAR      = '2024-03'
MARKET_CAP_YEAR    = 2024
VALUATION_OUTPUT   = 'output/valuation_summary.xlsx'
FLAGS_OUTPUT       = 'output/valuation_flags.csv'


# ── Data Loader ───────────────────────────────────────────────────────────────

def load_valuation_data():
    """
    Loads financial ratios, market cap, and sector mapping.

    Returns:
        DataFrame: Merged valuation dataset
    """
    from src.etl.loader import load_all_data

    data = load_all_data()
    market_cap = data['market_cap']
    sectors    = data['sectors']

    conn   = sqlite3.connect(DB_PATH)
    ratios = pd.read_sql_query(
        "SELECT * FROM financial_ratios_computed", conn
    )
    conn.close()

    # Latest ratios
    latest_ratios = ratios[ratios['year'] == ANALYSIS_YEAR].copy()

    # Latest market cap
    latest_mc = market_cap[market_cap['year'] == MARKET_CAP_YEAR][[
        'company_id', 'market_cap_crore', 'pe_ratio', 'pb_ratio', 'ev_ebitda'
    ]].copy()

    # Merge
    val_df = pd.merge(latest_ratios, latest_mc, on='company_id', how='left')
    val_df = pd.merge(
        val_df,
        sectors[['company_id', 'broad_sector']],
        on='company_id', how='left'
    )

    return val_df


# ── FCF Yield Computation ─────────────────────────────────────────────────────

def compute_fcf_yield(df):
    """
    Computes Free Cash Flow Yield as a percentage of market cap.

    FCF Yield = (Free Cash Flow / Market Cap) × 100

    Interpretation:
        > 10%  = Excellent (high cash generation, likely undervalued)
        5-10%  = Good
        2-5%   = Fair
        < 2%   = Low (expensive or weak cash generation)

    Args:
        df: Valuation DataFrame

    Returns:
        DataFrame: Input with fcf_yield_pct and fcf_yield_band columns
    """
    df = df.copy()

    df['fcf_yield_pct'] = np.where(
        (df['free_cash_flow_cr'].notna()) & (df['market_cap_crore'] > 0),
        (df['free_cash_flow_cr'] / df['market_cap_crore'] * 100).round(2),
        np.nan
    )

    def get_fcf_band(yield_pct):
        if pd.isna(yield_pct):
            return 'N/A'
        elif yield_pct > 10:
            return 'Excellent'
        elif yield_pct > 5:
            return 'Good'
        elif yield_pct > 2:
            return 'Fair'
        else:
            return 'Low'

    df['fcf_yield_band'] = df['fcf_yield_pct'].apply(get_fcf_band)

    return df


# ── Sector-Relative P/E Analysis ──────────────────────────────────────────────

def compute_sector_pe_metrics(df):
    """
    Computes sector-relative P/E valuation flags.

    For each company, compares P/E to sector median:
        - Caution: P/E > sector_median × 1.5 (expensive)
        - Discount: P/E < sector_median × 0.7 (cheap)
        - Fair: Everything else

    Args:
        df: Valuation DataFrame

    Returns:
        DataFrame: Input with P/E analysis columns
    """
    df = df.copy()

    # Sector median P/E
    sector_pe_median = df.groupby('broad_sector')['pe_ratio'].median()
    df['sector_median_pe'] = df['broad_sector'].map(sector_pe_median)

    # P/E vs sector median %
    df['pe_vs_sector_pct'] = np.where(
        df['sector_median_pe'].notna() & (df['sector_median_pe'] > 0),
        ((df['pe_ratio'] - df['sector_median_pe']) /
         df['sector_median_pe'] * 100).round(1),
        np.nan
    )

    # Valuation flag
    def get_valuation_flag(pe, sector_pe):
        if pd.isna(pe) or pd.isna(sector_pe):
            return 'N/A'

        ratio = pe / sector_pe
        if ratio > 1.5:
            return 'Caution'
        elif ratio < 0.7:
            return 'Discount'
        else:
            return 'Fair'

    df['valuation_flag'] = df.apply(
        lambda row: get_valuation_flag(
            row['pe_ratio'], row['sector_median_pe']
        ),
        axis=1
    )

    return df


# ── Export to Excel ───────────────────────────────────────────────────────────

def export_valuation_excel(val_df, output_path=VALUATION_OUTPUT):
    """
    Exports valuation summary to Excel file.

    Args:
        val_df:      Valuation DataFrame
        output_path: Path to save Excel file
    """
    output_cols = [
        'company_id', 'broad_sector',
        'pe_ratio', 'pb_ratio', 'ev_ebitda',
        'free_cash_flow_cr', 'market_cap_crore',
        'fcf_yield_pct', 'fcf_yield_band',
        'sector_median_pe', 'pe_vs_sector_pct', 'valuation_flag'
    ]

    val_export = val_df[output_cols].copy()
    val_export = val_export.sort_values(
        'fcf_yield_pct', ascending=False, na_position='last'
    )

    val_export.to_excel(output_path, index=False)
    print(f"Saved: {output_path}")
    print(f"Rows: {len(val_export)}")


# ── Export Flagged Companies ──────────────────────────────────────────────────

def export_valuation_flags(val_df, output_path=FLAGS_OUTPUT):
    """
    Exports only flagged companies (Caution or Discount) to CSV.

    Args:
        val_df:      Valuation DataFrame
        output_path: Path to save CSV file
    """
    flagged = val_df[
        val_df['valuation_flag'].isin(['Caution', 'Discount'])
    ][[
        'company_id', 'broad_sector', 'pe_ratio', 'sector_median_pe',
        'pe_vs_sector_pct', 'fcf_yield_pct', 'valuation_flag'
    ]].copy()

    flagged = flagged.sort_values('valuation_flag')
    flagged.to_csv(output_path, index=False)

    print(f"Saved: {output_path}")
    print(f"Flagged companies: {len(flagged)}")


# ── Master Runner ─────────────────────────────────────────────────────────────

def run_valuation_analysis():
    """
    Master function — loads data, computes all valuation metrics,
    and exports to Excel and CSV.

    Returns:
        DataFrame: Valuation analysis DataFrame

    Example:
        from src.analytics.valuation import run_valuation_analysis
        val_df = run_valuation_analysis()
    """
    print("Loading valuation data...")
    val_df = load_valuation_data()

    print("Computing FCF yield...")
    val_df = compute_fcf_yield(val_df)

    print("Computing sector P/E metrics...")
    val_df = compute_sector_pe_metrics(val_df)

    print("\nExporting to Excel...")
    export_valuation_excel(val_df)

    print("\nExporting flagged companies...")
    export_valuation_flags(val_df)

    print("\nValuation Summary:")
    print(f"  Companies analyzed: {val_df.dropna(subset=['pe_ratio']).shape[0]}")
    print(f"  Fair: {(val_df['valuation_flag'] == 'Fair').sum()}")
    print(f"  Discount: {(val_df['valuation_flag'] == 'Discount').sum()}")
    print(f"  Caution: {(val_df['valuation_flag'] == 'Caution').sum()}")
    print()
    print("Top 5 by FCF Yield:")
    print(val_df.nlargest(5, 'fcf_yield_pct')[
        ['company_id', 'fcf_yield_pct', 'valuation_flag']
    ].to_string(index=False))

    return val_df


# ── Run directly for testing ──────────────────────────────────────────────────

if __name__ == "__main__":
    val_df = run_valuation_analysis()
