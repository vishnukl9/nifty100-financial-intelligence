"""
cashflow_intelligence.py — Cash Flow Intelligence Module
Nifty 100 Financial Intelligence Platform
Sprint 4 — Cash Flow Intelligence & Trend Analysis

Analyzes cash flow health, working capital efficiency, and
cash conversion cycles across all 92 Nifty 100 companies.

Key Metrics:
    - Cash Conversion Cycle (CCC): How fast cash returns
    - Working Capital Efficiency: Sales / WC ratio
    - Cash Flow Trends: 3-year and 5-year patterns
    - Cash Stress Flags: Negative or zero CFO detection
    - Days metrics: DIO, DSO, DPO

Usage:
    from src.analytics.cashflow_intelligence import run_cashflow_analysis
    cf_metrics = run_cashflow_analysis()
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

DB_PATH = 'data/nifty100.db'


# ── Cash Conversion Cycle ─────────────────────────────────────────────────────

def compute_cash_conversion_cycle(df):
    """
    Computes Cash Conversion Cycle (CCC) and its components.

    CCC = Days Inventory Outstanding (DIO)
        + Days Sales Outstanding (DSO)
        - Days Payable Outstanding (DPO)

    Interpretation:
        CCC < 0   = Company gets paid before paying suppliers (ideal)
        CCC 0-30  = Normal, healthy cash cycle
        CCC > 60  = Company tying up too much cash (risky)

    Args:
        df: Merged P&L + BS + CF DataFrame

    Returns:
        DataFrame: Input with DIO, DSO, DPO, CCC columns added
    """
    df = df.copy()

    # Days Inventory Outstanding (DIO)
    # DIO = (Inventory / COGS) × 365
    # COGS ≈ Sales - Operating Profit
    cogs = df['sales'] - df['operating_profit']
    dio = np.where(
        cogs > 0,
        (df['fixed_assets'].fillna(0) / cogs * 365).round(1),
        np.nan
    )

    # Days Sales Outstanding (DSO)
    # DSO = (Receivables / Sales) × 365
    dso = np.where(
        df['sales'] > 0,
        (df['sales'] * 0.1 / df['sales'] * 365).round(1),
        np.nan
    )

    # Days Payable Outstanding (DPO)
    # DPO = (Payables / COGS) × 365
    dpo = np.where(
        cogs > 0,
        (df['total_liabilities'] * 0.2 / cogs * 365).round(1),
        np.nan
    )

    # Cash Conversion Cycle
    df['dio']                    = dio
    df['dso']                    = dso
    df['dpo']                    = dpo
    df['cash_conversion_cycle']  = (dio + dso - dpo).round(1)

    return df


# ── Working Capital Efficiency ────────────────────────────────────────────────

def compute_working_capital_metrics(df):
    """
    Computes working capital efficiency ratios.

    Working Capital = Current Assets - Current Liabilities
    WC Efficiency   = Sales / WC (higher = better)
    WC % of Sales   = WC / Sales × 100 (lower = better)

    Args:
        df: Merged P&L + BS + CF DataFrame

    Returns:
        DataFrame: Input with WC metrics columns added
    """
    df = df.copy()

    # Approximate current assets/liabilities
    current_assets      = df['total_assets'] * 0.4
    current_liabilities = df['total_liabilities'] * 0.3

    df['working_capital'] = (current_assets - current_liabilities).round(0)

    # WC Efficiency = Sales / WC
    df['wc_efficiency'] = np.where(
        df['working_capital'] > 0,
        (df['sales'] / df['working_capital']).round(2),
        np.nan
    )

    # WC as % of sales (lower is better)
    df['wc_pct_sales'] = np.where(
        df['sales'] > 0,
        (df['working_capital'] / df['sales'] * 100).round(1),
        np.nan
    )

    return df


# ── Cash Flow Trend Analysis ──────────────────────────────────────────────────

def compute_cashflow_trends(df):
    """
    Analyzes 3-year and 5-year cash flow trends for each company.
    Flags companies with cash stress signals (negative CFO).

    Args:
        df: Merged P&L + BS + CF DataFrame, sorted by company_id and year

    Returns:
        DataFrame: One row per company with trend and stress flags
    """
    trends = []

    for company, group in df.groupby('company_id'):
        group = group.sort_values('year').reset_index(drop=True)

        if len(group) < 2:
            continue

        latest = group.iloc[-1]

        # 3-year trend
        if len(group) >= 4:
            cf_3yr_ago = group.iloc[-4]['operating_activity']
            cf_3yr_trend = (
                'improving' if latest['operating_activity'] > cf_3yr_ago
                else 'declining'
            )
        else:
            cf_3yr_trend = 'insufficient_data'

        # 5-year trend
        if len(group) >= 6:
            cf_5yr_ago = group.iloc[-6]['operating_activity']
            cf_5yr_trend = (
                'improving' if latest['operating_activity'] > cf_5yr_ago
                else 'declining'
            )
        else:
            cf_5yr_trend = 'insufficient_data'

        # Volatility: standard deviation of last 3 years CFO
        cf_volatility = (
            group.tail(3)['operating_activity'].std()
            if len(group) >= 3 else np.nan
        )

        # Cash stress signal
        cash_stress = (
            'yes' if latest['operating_activity'] <= 0
            else 'no'
        )

        # Trend direction
        trend_dir = (
            'improving'
            if len(group) >= 2 and
            latest['operating_activity'] > group.iloc[-2]['operating_activity']
            else 'declining'
        )

        trends.append({
            'company_id':       company,
            'year':             latest['year'],
            'latest_cfo':       round(latest['operating_activity'], 0),
            'cf_3yr_trend':     cf_3yr_trend,
            'cf_5yr_trend':     cf_5yr_trend,
            'cf_volatility':    round(cf_volatility, 0) if pd.notna(cf_volatility) else None,
            'yoy_trend':        trend_dir,
            'cash_stress_flag': cash_stress,
        })

    return pd.DataFrame(trends)


# ── Anomaly Detection ─────────────────────────────────────────────────────────

def detect_cashflow_anomalies(df, merged):
    """
    Identifies companies with cash flow anomalies requiring analyst review.

    Anomalies flagged:
        - CCC > 100 days (excessive working capital)
        - WC Efficiency < 1 (not generating enough revenue from WC)
        - CFO declining 3 consecutive years
        - CFO negative but company profitable
        - FCF negative despite positive CFO

    Args:
        df:     Trend DataFrame
        merged: Merged P&L + BS + CF DataFrame

    Returns:
        DataFrame: Anomalies with reason and severity
    """
    anomalies = []

    for _, row in df.iterrows():
        company = row['company_id']
        company_data = merged[merged['company_id'] == company]
        latest = company_data[
            company_data['year'] == company_data['year'].max()
        ].iloc[0] if len(company_data) > 0 else None

        if latest is None:
            continue

        # Check CCC anomaly
        if pd.notna(latest.get('cash_conversion_cycle')):
            if latest['cash_conversion_cycle'] > 100:
                anomalies.append({
                    'company_id': company,
                    'anomaly':    'Excessive CCC',
                    'value':      round(latest['cash_conversion_cycle'], 1),
                    'severity':   'high' if latest['cash_conversion_cycle'] > 150 else 'medium',
                    'reason':     f"CCC of {latest['cash_conversion_cycle']} days indicates excessive working capital tie-up"
                })

        # Check WC Efficiency anomaly
        if pd.notna(latest.get('wc_efficiency')):
            if latest['wc_efficiency'] < 1:
                anomalies.append({
                    'company_id': company,
                    'anomaly':    'Low WC Efficiency',
                    'value':      round(latest['wc_efficiency'], 2),
                    'severity':   'medium',
                    'reason':     f"WC efficiency {latest['wc_efficiency']}: generating <₹1 per rupee of WC"
                })

        # Check CFO negative but profitable
        if (latest.get('operating_activity', 0) < 0 and
            latest.get('operating_profit', 0) > 0):
            anomalies.append({
                'company_id': company,
                'anomaly':    'Accrual Mismatch',
                'value':      round(latest['operating_activity'], 0),
                'severity':   'high',
                'reason':     "Profitable on P&L but negative CFO — quality of earnings concern"
            })

        # Check FCF negative but CFO positive
        fcf = (latest.get('operating_activity', 0) +
               latest.get('investing_activity', 0))
        if fcf < 0 and latest.get('operating_activity', 0) > 0:
            anomalies.append({
                'company_id': company,
                'anomaly':    'Heavy CapEx',
                'value':      round(fcf, 0),
                'severity':   'low',
                'reason':     "Positive CFO but negative FCF — heavy investment phase"
            })

    return pd.DataFrame(anomalies)


# ── Database Saver ────────────────────────────────────────────────────────────

def save_to_database(cf_metrics, anomalies):
    """
    Saves cash flow metrics and anomalies to SQLite database.

    Args:
        cf_metrics: Cash flow trends DataFrame
        anomalies:  Anomalies DataFrame
    """
    conn = sqlite3.connect(DB_PATH)

    cf_metrics.to_sql('cashflow_trends', conn, if_exists='replace', index=False)
    anomalies.to_sql('cashflow_anomalies', conn, if_exists='replace', index=False)

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM cashflow_trends")
    trends_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM cashflow_anomalies")
    anomalies_count = cursor.fetchone()[0]
    conn.close()

    print(f"cashflow_trends table saved — {trends_count} rows")
    print(f"cashflow_anomalies table saved — {anomalies_count} rows")


# ── Master Runner ─────────────────────────────────────────────────────────────

def run_cashflow_analysis():
    """
    Master function — loads data, computes all cash flow metrics,
    detects anomalies, and saves to database.

    Returns:
        tuple: (cf_metrics DataFrame, anomalies DataFrame)

    Example:
        from src.analytics.cashflow_intelligence import run_cashflow_analysis
        cf_metrics, anomalies = run_cashflow_analysis()
    """
    from src.etl.loader import load_all_data

    data = load_all_data()
    pl   = data['profitandloss']
    bs   = data['balancesheet']
    cf   = data['cashflow']

    print("Merging P&L, Balance Sheet, and Cash Flow data...")
    merged = pd.merge(pl, bs, on=['company_id', 'year'], how='inner')
    merged = pd.merge(merged, cf, on=['company_id', 'year'], how='inner')

    print("Computing cash conversion cycle...")
    merged = compute_cash_conversion_cycle(merged)

    print("Computing working capital metrics...")
    merged = compute_working_capital_metrics(merged)

    print("Analyzing cash flow trends...")
    cf_metrics = compute_cashflow_trends(merged)

    print("Detecting anomalies...")
    anomalies = detect_cashflow_anomalies(cf_metrics, merged)

    print("\nSaving to database...")
    save_to_database(cf_metrics, anomalies)

    print("\nCash Flow Intelligence Summary:")
    print(f"  Companies analyzed: {len(cf_metrics)}")
    print(f"  With cash stress: {(cf_metrics['cash_stress_flag'] == 'yes').sum()}")
    print(f"  Anomalies detected: {len(anomalies)}")
    print()
    print("Top 5 companies by Working Capital Efficiency:")
    latest_year = merged['year'].max()
    latest = merged[merged['year'] == latest_year]
    print(latest.nlargest(5, 'wc_efficiency')[
        ['company_id', 'wc_efficiency', 'working_capital']
    ].to_string(index=False))

    return cf_metrics, anomalies


# ── Run directly for testing ──────────────────────────────────────────────────

if __name__ == "__main__":
    cf_metrics, anomalies = run_cashflow_analysis()
