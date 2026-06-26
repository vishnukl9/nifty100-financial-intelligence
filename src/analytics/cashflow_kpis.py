"""
cashflow_kpis.py — Cash Flow KPI Engine
Nifty 100 Financial Intelligence Platform
Sprint 2 — Financial Ratio Engine

This module computes cash flow quality metrics and capital
allocation patterns for all 92 Nifty 100 companies.

KPIs Computed:
    - Free Cash Flow (FCF)
    - CFO Quality Score (CFO / Net Profit)
    - CFO Quality Label (High Quality / Moderate / Accrual Risk)
    - CapEx (absolute investing activity)
    - CapEx Intensity (CapEx / Sales %)
    - CapEx Label (Asset Light / Moderate / Capital Intensive)
    - Capital Allocation Pattern (CFO/CFI/CFF sign pattern)
    - Capital Allocation Label (Reinvestor / Distress Signal etc.)

Usage:
    from src.analytics.cashflow_kpis import compute_all_cashflow_kpis
    cf_kpis = compute_all_cashflow_kpis()
"""

import pandas as pd
import numpy as np
import os
import sys

# ── Path Configuration ────────────────────────────────────────────────────────

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(PROJECT_PATH)
os.chdir(PROJECT_PATH)

# ── Free Cash Flow ────────────────────────────────────────────────────────────

def compute_fcf(df):
    """
    Free Cash Flow = CFO + CFI
    Positive = generating cash after investments
    Negative = burning cash

    Args:
        df: Merged DataFrame with operating and investing activity columns

    Returns:
        DataFrame with free_cash_flow_cr column added
    """
    df = df.copy()
    df['free_cash_flow_cr'] = (
        df['operating_activity'] + df['investing_activity']
    ).round(2)
    return df


# ── CFO Quality Score ─────────────────────────────────────────────────────────

def compute_cfo_quality(df):
    """
    CFO Quality Score = CFO / Net Profit
    > 1.0 = High Quality Earnings (cash exceeds profit)
    > 0.5 = Moderate Quality
    < 0.5 = Accrual Risk (profit not backed by real cash)
    None  = net profit is zero

    Args:
        df: Merged DataFrame with operating_activity and net_profit

    Returns:
        DataFrame with cfo_quality_score and cfo_quality_label added
    """
    df = df.copy()

    df['cfo_quality_score'] = np.where(
        df['net_profit'] != 0,
        (df['operating_activity'] / df['net_profit']).round(2),
        np.nan
    )
    df['cfo_quality_score'] = pd.to_numeric(
        df['cfo_quality_score'], errors='coerce'
    )

    def quality_label(score):
        if pd.isna(score):
            return 'N/A'
        elif score > 1.0:
            return 'High Quality'
        elif score > 0.5:
            return 'Moderate'
        else:
            return 'Accrual Risk'

    df['cfo_quality_label'] = df['cfo_quality_score'].apply(quality_label)
    return df


# ── CapEx Intensity ───────────────────────────────────────────────────────────

def compute_capex_intensity(df):
    """
    CapEx = |Investing Activity| (proxy for capital expenditure)
    CapEx Intensity = CapEx / Sales × 100

    < 3%  = Asset Light  (IT, FMCG, Consumer)
    3-8%  = Moderate
    > 8%  = Capital Intensive (Steel, Power, Energy)

    Args:
        df: Merged DataFrame with investing_activity and sales

    Returns:
        DataFrame with capex_cr, capex_intensity_pct, capex_label added
    """
    df = df.copy()

    df['capex_cr'] = df['investing_activity'].abs().round(2)

    df['capex_intensity_pct'] = np.where(
        df['sales'] > 0,
        (df['capex_cr'] / df['sales'] * 100).round(2),
        np.nan
    )
    df['capex_intensity_pct'] = pd.to_numeric(
        df['capex_intensity_pct'], errors='coerce'
    )

    def capex_label(pct):
        if pd.isna(pct):
            return 'N/A'
        elif pct < 3:
            return 'Asset Light'
        elif pct < 8:
            return 'Moderate'
        else:
            return 'Capital Intensive'

    df['capex_label'] = df['capex_intensity_pct'].apply(capex_label)
    return df


# ── Capital Allocation Pattern ────────────────────────────────────────────────

def get_capital_allocation_pattern(cfo, cfi, cff):
    """
    Classifies capital allocation based on sign pattern of CFO, CFI, CFF.

    Pattern Map:
        (+,-,-) → Reinvestor        — ideal: ops fund investment + debt repay
        (+,-,+) → Aggressive Expander — ops + debt fund heavy investment
        (+,+,-) → Asset Seller      — selling assets, returning to shareholders
        (+,+,+) → Cash Accumulator  — building cash reserves
        (-,-,+) → Distress Signal   — raising funds to cover ops + investment
        (-,+,+) → Distress Signal   — selling assets + raising funds for ops
        (-,-,-) → Contraction       — everything shrinking
        (-,+,-) → Restructuring     — selling assets to repay debt

    Args:
        cfo: Cash from Operating Activities
        cfi: Cash from Investing Activities
        cff: Cash from Financing Activities

    Returns:
        tuple: (pattern string, label string)
    """
    cfo_sign = '+' if cfo >= 0 else '-'
    cfi_sign = '+' if cfi >= 0 else '-'
    cff_sign = '+' if cff >= 0 else '-'
    pattern  = f"({cfo_sign},{cfi_sign},{cff_sign})"

    pattern_map = {
        '(+,-,-)': 'Reinvestor',
        '(+,-,+)': 'Aggressive Expander',
        '(+,+,-)': 'Asset Seller',
        '(+,+,+)': 'Cash Accumulator',
        '(-,-,+)': 'Distress Signal',
        '(-,+,+)': 'Distress Signal',
        '(-,-,-)': 'Contraction',
        '(-,+,-)': 'Restructuring',
    }

    return pattern, pattern_map.get(pattern, 'Other')


def compute_capital_allocation(df):
    """
    Applies capital allocation pattern classification to all rows.

    Args:
        df: DataFrame with operating, investing, financing activity columns

    Returns:
        DataFrame with cf_pattern and cf_label columns added
    """
    df = df.copy()
    df[['cf_pattern', 'cf_label']] = df.apply(
        lambda row: pd.Series(get_capital_allocation_pattern(
            row['operating_activity'],
            row['investing_activity'],
            row['financing_activity']
        )), axis=1
    )
    return df


# ── Master Cash Flow KPI Computer ─────────────────────────────────────────────

def compute_all_cashflow_kpis():
    """
    Computes all cash flow KPIs for all companies across all years.

    Returns:
        DataFrame: All cash flow KPIs with company_id and year as keys

    Example:
        from src.analytics.cashflow_kpis import compute_all_cashflow_kpis
        cf_kpis = compute_all_cashflow_kpis()
    """
    from src.etl.loader import load_all_data

    data = load_all_data()
    cf   = data['cashflow']
    pl   = data['profitandloss']

    # Merge cash flow with P&L
    merged = pd.merge(
        cf,
        pl[['company_id', 'year', 'sales',
            'net_profit', 'operating_profit']],
        on=['company_id', 'year'],
        how='inner'
    )

    print("Computing Free Cash Flow...")
    merged = compute_fcf(merged)

    print("Computing CFO Quality Score...")
    merged = compute_cfo_quality(merged)

    print("Computing CapEx Intensity...")
    merged = compute_capex_intensity(merged)

    print("Computing Capital Allocation Patterns...")
    merged = compute_capital_allocation(merged)

    # Select output columns
    output_cols = [
        'company_id', 'year',
        'operating_activity',
        'investing_activity',
        'financing_activity',
        'free_cash_flow_cr',
        'cfo_quality_score',
        'cfo_quality_label',
        'capex_cr',
        'capex_intensity_pct',
        'capex_label',
        'cf_pattern',
        'cf_label',
    ]

    result = merged[output_cols].copy()

    print(f"\nCash Flow KPI Engine Complete!")
    print(f"  Total rows:   {len(result)}")
    print(f"  Companies:    {result['company_id'].nunique()}")
    print(f"  KPIs:         {len(output_cols) - 2}")

    return result


# ── Run directly for testing ──────────────────────────────────────────────────

if __name__ == "__main__":
    cf_kpis = compute_all_cashflow_kpis()

    print("\nSample — Key Companies (Latest Year):")
    latest = cf_kpis[cf_kpis['year'] == '2024-03']
    sample = latest[latest['company_id'].isin(
        ['TCS', 'RELIANCE', 'HDFCBANK', 'INFY']
    )][['company_id', 'free_cash_flow_cr',
        'cfo_quality_label', 'capex_label', 'cf_label']]
    print(sample.to_string(index=False))
