"""
ratios.py — Financial Ratio Engine
Nifty 100 Financial Intelligence Platform
Sprint 2 — Financial Ratio Engine

This module computes profitability, leverage, and efficiency
ratios for all 92 Nifty 100 companies across all available years.

Ratios computed:
    Profitability:
        - Net Profit Margin (NPM)
        - Operating Profit Margin (OPM)
        - Return on Equity (ROE)
        - Return on Capital Employed (ROCE)
    Leverage:
        - Debt to Equity (D/E)
        - Interest Coverage Ratio (ICR)
        - Net Debt
    Efficiency:
        - Asset Turnover
        - Fixed Asset Turnover

Usage:
    from src.analytics.ratios import compute_all_ratios
    ratios_df = compute_all_ratios()
"""

import pandas as pd
import numpy as np
import os
import sys

# ── Path Configuration ────────────────────────────────────────────────────────

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(PROJECT_PATH)
os.chdir(PROJECT_PATH)

# ── Data Loader ───────────────────────────────────────────────────────────────

def load_merged_data():
    """
    Loads and merges P&L and Balance Sheet data for ratio computation.

    Returns:
        DataFrame: Merged P&L + Balance Sheet with all required columns
    """
    from src.etl.loader import load_all_data

    data = load_all_data()
    pl   = data['profitandloss']
    bs   = data['balancesheet']

    merged = pd.merge(
        pl,
        bs[['company_id', 'year', 'equity_capital', 'reserves',
            'borrowings', 'total_assets', 'fixed_assets',
            'investments', 'other_liabilities']],
        on=['company_id', 'year'],
        how='inner'
    )

    # Compute total equity for reuse
    merged['total_equity'] = merged['equity_capital'] + merged['reserves']

    return merged


# ── Profitability Ratios ──────────────────────────────────────────────────────

def compute_npm(df):
    """
    Net Profit Margin = Net Profit / Sales × 100
    Returns None if Sales is zero or missing.

    Benchmark: >10% good, >20% excellent
    """
    df = df.copy()
    df['net_profit_margin_pct'] = np.where(
        df['sales'] > 0,
        (df['net_profit'] / df['sales'] * 100).round(2),
        None
    )
    return df


def compute_opm(df):
    """
    Operating Profit Margin = Operating Profit / Sales × 100
    Returns None if Sales is zero or missing.

    Benchmark: >15% good, >25% excellent
    """
    df = df.copy()
    df['operating_profit_margin_pct'] = np.where(
        df['sales'] > 0,
        (df['operating_profit'] / df['sales'] * 100).round(2),
        None
    )
    return df


def compute_roe(df):
    """
    Return on Equity = Net Profit / (Equity Capital + Reserves) × 100
    Returns None if total equity is zero or negative.

    Benchmark: >15% good, >20% excellent
    """
    df = df.copy()
    df['return_on_equity_pct'] = np.where(
        df['total_equity'] > 0,
        (df['net_profit'] / df['total_equity'] * 100).round(2),
        None
    )
    return df


def compute_roce(df):
    """
    ROCE = EBIT / (Equity + Reserves + Borrowings) × 100
    EBIT = Operating Profit - Depreciation
    Returns None if capital employed is zero or negative.

    Benchmark: >15% good, >25% excellent
    """
    df = df.copy()

    # EBIT = Operating Profit - Depreciation
    df['ebit'] = df['operating_profit'] - df['depreciation']

    # Capital Employed = Total Equity + Borrowings
    df['capital_employed'] = df['total_equity'] + df['borrowings']

    df['return_on_capital_pct'] = np.where(
        df['capital_employed'] > 0,
        (df['ebit'] / df['capital_employed'] * 100).round(2),
        None
    )
    return df


# ── Leverage Ratios ───────────────────────────────────────────────────────────

def compute_de_ratio(df):
    """
    Debt to Equity = Borrowings / (Equity Capital + Reserves)
    Returns 0 if debt free.
    Returns None if equity is zero or negative.

    Benchmark: <1.0 healthy, <0.5 conservative
    Flag: >5 for non-financial companies
    """
    df = df.copy()
    df['debt_to_equity'] = np.where(
        df['total_equity'] > 0,
        (df['borrowings'] / df['total_equity']).round(2),
        None
    )
    return df


def compute_icr(df):
    """
    Interest Coverage = (Operating Profit + Other Income) / Interest
    Returns None if interest is zero (debt free company).
    Returns None if result would be infinite.

    Benchmark: >3x safe, >5x strong
    Flag: <1x critical risk
    """
    df = df.copy()
    df['interest_coverage'] = np.where(
        df['interest'] > 0,
        ((df['operating_profit'] + df['other_income']) /
         df['interest']).round(2),
        None
    )
    return df


def compute_net_debt(df):
    """
    Net Debt = Borrowings - Investments
    Negative value means company has more cash/investments than debt.

    A negative net debt is a positive sign (net cash positive).
    """
    df = df.copy()
    df['net_debt'] = (df['borrowings'] - df['investments']).round(2)
    return df


# ── Efficiency Ratios ─────────────────────────────────────────────────────────

def compute_asset_turnover(df):
    """
    Asset Turnover = Sales / Total Assets
    Returns NaN if total assets is zero.

    Benchmark: >1x efficient, >2x asset-light
    """
    df = df.copy()
    df['asset_turnover'] = np.where(
        df['total_assets'] > 0,
        (df['sales'] / df['total_assets']).round(2),
        np.nan
    )
    df['asset_turnover'] = pd.to_numeric(df['asset_turnover'], errors='coerce')
    return df


def compute_fixed_asset_turnover(df):
    """
    Fixed Asset Turnover = Sales / Fixed Assets
    Returns NaN if fixed assets is zero (service companies).

    Benchmark: >3x good
    """
    df = df.copy()
    df['fixed_asset_turnover'] = np.where(
        df['fixed_assets'] > 0,
        (df['sales'] / df['fixed_assets']).round(2),
        np.nan
    )
    df['fixed_asset_turnover'] = pd.to_numeric(
        df['fixed_asset_turnover'], errors='coerce'
    )
    return df


# ── Master Ratio Computer ─────────────────────────────────────────────────────

def compute_all_ratios():
    """
    Computes all profitability, leverage, and efficiency ratios
    for all 92 companies across all available years.

    Returns:
        DataFrame: All ratios with company_id and year as keys

    Example:
        from src.analytics.ratios import compute_all_ratios
        ratios_df = compute_all_ratios()
    """
    print("Loading merged data...")
    df = load_merged_data()

    print("Computing profitability ratios...")
    df = compute_npm(df)
    df = compute_opm(df)
    df = compute_roe(df)
    df = compute_roce(df)

    print("Computing leverage ratios...")
    df = compute_de_ratio(df)
    df = compute_icr(df)
    df = compute_net_debt(df)

    print("Computing efficiency ratios...")
    df = compute_asset_turnover(df)
    df = compute_fixed_asset_turnover(df)

    # Select only the ratio columns for output
    ratio_cols = [
        'company_id', 'year',
        'net_profit_margin_pct',
        'operating_profit_margin_pct',
        'return_on_equity_pct',
        'return_on_capital_pct',
        'debt_to_equity',
        'interest_coverage',
        'net_debt',
        'asset_turnover',
        'fixed_asset_turnover',
        'ebit',
        'capital_employed',
        'total_equity',
    ]

    result = df[ratio_cols].copy()

    print(f"\nRatio Engine Complete!")
    print(f"  Total rows:    {len(result)}")
    print(f"  Companies:     {result['company_id'].nunique()}")
    print(f"  Year range:    {result['year'].min()} to {result['year'].max()}")
    print(f"  Ratios computed: {len(ratio_cols) - 2}")

    return result


# ── Run directly for testing ──────────────────────────────────────────────────

if __name__ == "__main__":
    ratios_df = compute_all_ratios()
    print("\nSample output:")
    print(ratios_df[ratios_df['company_id'] == 'TCS'].tail(3).to_string())
