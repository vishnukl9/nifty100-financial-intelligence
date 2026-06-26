"""
cagr.py — CAGR Growth Ratio Engine
Nifty 100 Financial Intelligence Platform
Sprint 2 — Financial Ratio Engine

This module computes Compound Annual Growth Rate (CAGR) for
Revenue, Net Profit (PAT) and EPS across 3yr, 5yr and 10yr
windows for all 92 Nifty 100 companies.

Edge Cases Handled:
    TURNAROUND      — base year negative, end year positive
    DECLINE_TO_LOSS — base year positive, end year negative
    BOTH_NEGATIVE   — both base and end year negative
    ZERO_BASE       — base year is zero
    INSUFFICIENT    — less than 3 years of data available
    OK              — normal CAGR computed successfully

Usage:
    from src.analytics.cagr import compute_all_cagr
    cagr_df = compute_all_cagr()
"""

import pandas as pd
import numpy as np
import os
import sys

# ── Path Configuration ────────────────────────────────────────────────────────

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(PROJECT_PATH)
os.chdir(PROJECT_PATH)

# ── Core CAGR Function ────────────────────────────────────────────────────────

def compute_cagr(start_value, end_value, n_years):
    """
    Computes CAGR with full edge case handling.

    Formula: ((End Value / Start Value) ^ (1/n) - 1) × 100

    Args:
        start_value: Value at start of period
        end_value:   Value at end of period
        n_years:     Number of years in the period

    Returns:
        tuple: (cagr_value or None, flag string)

    Examples:
        compute_cagr(100, 161, 5)  → (10.0, 'OK')
        compute_cagr(-100, 200, 5) → (None, 'TURNAROUND')
        compute_cagr(100, -50, 5)  → (None, 'DECLINE_TO_LOSS')
    """
    # Check for missing values
    if pd.isna(start_value) or pd.isna(end_value):
        return None, 'INSUFFICIENT'

    # Check for insufficient history
    if n_years < 3:
        return None, 'INSUFFICIENT'

    # Check for zero base — cannot divide by zero
    if start_value == 0:
        return None, 'ZERO_BASE'

    # Check for turnaround — negative to positive
    if start_value < 0 and end_value > 0:
        return None, 'TURNAROUND'

    # Check for decline to loss — positive to negative
    if start_value > 0 and end_value < 0:
        return None, 'DECLINE_TO_LOSS'

    # Check for both negative
    if start_value < 0 and end_value < 0:
        return None, 'BOTH_NEGATIVE'

    # Normal CAGR computation
    try:
        cagr = ((end_value / start_value) ** (1 / n_years) - 1) * 100
        return round(cagr, 2), 'OK'
    except Exception:
        return None, 'COMPUTE_ERROR'


# ── Company Level CAGR ────────────────────────────────────────────────────────

def compute_cagr_for_all(pl, metric, windows=None):
    """
    Computes CAGR for a given metric across all companies
    for multiple time windows.

    Args:
        pl:      Clean P&L DataFrame sorted by company_id and year
        metric:  Column name to compute CAGR for
                 e.g. 'sales', 'net_profit', 'eps'
        windows: List of year windows. Default: [3, 5, 10]

    Returns:
        DataFrame: company_id + CAGR value and flag for each window
    """
    if windows is None:
        windows = [3, 5, 10]

    results = []

    for company_id, group in pl.groupby('company_id'):
        group = group.sort_values('year').reset_index(drop=True)
        row   = {'company_id': company_id}

        for n in windows:
            col_name  = f'{metric}_cagr_{n}yr'
            flag_name = f'{metric}_cagr_{n}yr_flag'

            if len(group) >= n + 1:
                end_val   = group.iloc[-1][metric]
                start_val = group.iloc[-(n + 1)][metric]
                cagr, flag = compute_cagr(start_val, end_val, n)
            else:
                cagr, flag = None, 'INSUFFICIENT'

            row[col_name]  = cagr
            row[flag_name] = flag

        results.append(row)

    return pd.DataFrame(results)


# ── Master CAGR Computer ──────────────────────────────────────────────────────

def compute_all_cagr():
    """
    Computes Revenue, PAT and EPS CAGR for all companies
    across 3yr, 5yr and 10yr windows.

    Returns:
        DataFrame: All CAGR metrics with company_id as key

    Example:
        from src.analytics.cagr import compute_all_cagr
        cagr_df = compute_all_cagr()
    """
    from src.etl.loader import load_all_data

    data = load_all_data()
    pl   = data['profitandloss']

    print("Computing Revenue CAGR...")
    revenue_cagr = compute_cagr_for_all(pl, 'sales')

    print("Computing PAT CAGR...")
    pat_cagr = compute_cagr_for_all(pl, 'net_profit')

    print("Computing EPS CAGR...")
    eps_cagr = compute_cagr_for_all(pl, 'eps')

    # Merge all results
    cagr_df = revenue_cagr.merge(pat_cagr, on='company_id')
    cagr_df = cagr_df.merge(eps_cagr, on='company_id')

    print(f"\nCAGR Engine Complete!")
    print(f"  Companies:  {len(cagr_df)}")
    print(f"  Metrics:    Revenue, PAT, EPS")
    print(f"  Windows:    3yr, 5yr, 10yr")
    print(f"  Columns:    {len(cagr_df.columns) - 1} CAGR columns")

    return cagr_df


# ── Run directly for testing ──────────────────────────────────────────────────

if __name__ == "__main__":
    cagr_df = compute_all_cagr()

    print("\nSample — Key Companies (5yr CAGR):")
    cols = ['company_id', 'sales_cagr_5yr',
            'net_profit_cagr_5yr', 'eps_cagr_5yr']
    sample = cagr_df[cagr_df['company_id'].isin(
        ['TCS', 'RELIANCE', 'HDFCBANK', 'INFY', 'MARUTI']
    )][cols]
    print(sample.to_string(index=False))
