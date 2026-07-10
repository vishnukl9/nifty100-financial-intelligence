"""
sector_analytics.py — Sector Analytics Module
Nifty 100 Financial Intelligence Platform
Sprint 3 — Screener & Health Scoring

Aggregates financial KPIs by broad sector and generates
radar charts for all peer group companies.

Outputs:
    - sector_analytics table in SQLite
    - reports/radar_charts/ — PNG radar charts for all 56 companies

Usage:
    from src.analytics.sector_analytics import run_sector_analytics
    sector_agg = run_sector_analytics()
"""

import pandas as pd
import numpy as np
import sqlite3
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import sys

# ── Path Configuration ────────────────────────────────────────────────────────

PROJECT_PATH  = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(PROJECT_PATH)
os.chdir(PROJECT_PATH)

DB_PATH       = 'data/nifty100.db'
ANALYSIS_YEAR = '2024-03'
RADAR_DIR     = 'reports/radar_charts'

NUMERIC_COLS = [
    'return_on_equity_pct', 'return_on_capital_pct',
    'net_profit_margin_pct', 'debt_to_equity',
    'free_cash_flow_cr', 'sales_cagr_5yr',
    'net_profit_cagr_5yr', 'interest_coverage', 'asset_turnover'
]

RADAR_METRICS = [
    'return_on_equity_pct',
    'return_on_capital_pct',
    'net_profit_margin_pct',
    'debt_to_equity',
    'free_cash_flow_cr',
    'net_profit_cagr_5yr',
    'sales_cagr_5yr',
    'interest_coverage',
]

METRIC_LABELS = {
    'return_on_equity_pct':   'ROE',
    'return_on_capital_pct':  'ROCE',
    'net_profit_margin_pct':  'NPM',
    'debt_to_equity':         'D/E',
    'free_cash_flow_cr':      'FCF',
    'net_profit_cagr_5yr':    'PAT\nCAGR',
    'sales_cagr_5yr':         'Rev\nCAGR',
    'eps_cagr_5yr':           'EPS\nCAGR',
    'interest_coverage':      'ICR',
    'asset_turnover':         'Asset\nTO',
}


# ── Radar Chart ───────────────────────────────────────────────────────────────

def plot_radar_chart(company_id, group_name, company_values,
                     group_avg_values, metrics, output_dir=RADAR_DIR):
    """
    Generates and saves a radar chart for a company vs peer group average.

    Args:
        company_id:        NSE ticker
        group_name:        Peer group name
        company_values:    List of percentile ranks for the company
        group_avg_values:  List of average percentile ranks for the group
        metrics:           List of metric names for each axis
        output_dir:        Directory to save PNG files

    Returns:
        str: Path to saved PNG file
    """
    N      = len(metrics)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    company_values   = list(company_values)   + [company_values[0]]
    group_avg_values = list(group_avg_values) + [group_avg_values[0]]
    labels           = [METRIC_LABELS.get(m, m) for m in metrics]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    ax.plot(angles, company_values, 'o-', linewidth=2,
            color='#1F4E79', label=company_id)
    ax.fill(angles, company_values, alpha=0.25, color='#1F4E79')

    ax.plot(angles, group_avg_values, 'o--', linewidth=1.5,
            color='#ED7D31', label='Peer Avg')
    ax.fill(angles, group_avg_values, alpha=0.10, color='#ED7D31')

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=10)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.50, 0.75, 1.0])
    ax.set_yticklabels(['25th', '50th', '75th', '100th'], size=8)
    ax.grid(color='grey', linestyle='--', linewidth=0.5, alpha=0.7)

    ax.set_title(
        f"{company_id} — {group_name}\nPeer Percentile Ranks",
        size=13, fontweight='bold', pad=20
    )
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))

    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{company_id}_radar.png")
    plt.tight_layout()
    plt.savefig(filepath, dpi=100, bbox_inches='tight')
    plt.close()

    return filepath


# ── Radar Chart Generator ─────────────────────────────────────────────────────

def generate_all_radar_charts(peer_percentiles):
    """
    Generates radar charts for all companies in all peer groups.

    Args:
        peer_percentiles: Long format peer percentiles DataFrame

    Returns:
        tuple: (generated list, failed list)
    """
    generated = []
    failed    = []

    for group_name in peer_percentiles['peer_group_name'].unique():
        group_data = peer_percentiles[
            peer_percentiles['peer_group_name'] == group_name
        ]

        available_metrics = [
            m for m in RADAR_METRICS
            if m in group_data['metric'].values
        ]

        if len(available_metrics) < 3:
            continue

        group_avg  = group_data.groupby('metric')['percentile_rank'].mean()
        companies  = group_data['company_id'].unique()

        for company_id in companies:
            company_data = group_data[
                group_data['company_id'] == company_id
            ].set_index('metric')

            company_vals = []
            avg_vals     = []

            for metric in available_metrics:
                c_val = company_data.loc[metric, 'percentile_rank'] \
                        if metric in company_data.index else 0.5
                a_val = group_avg.get(metric, 0.5)
                company_vals.append(
                    float(c_val) if pd.notna(c_val) else 0.5
                )
                avg_vals.append(
                    float(a_val) if pd.notna(a_val) else 0.5
                )

            try:
                plot_radar_chart(
                    company_id, group_name,
                    company_vals, avg_vals, available_metrics
                )
                generated.append(company_id)
            except Exception as e:
                failed.append((company_id, str(e)))

    return generated, failed


# ── Sector Analytics ──────────────────────────────────────────────────────────

def compute_sector_analytics(ratios, sectors):
    """
    Computes median KPIs aggregated by broad sector.

    Args:
        ratios:  financial_ratios_computed DataFrame
        sectors: sectors DataFrame with broad_sector mapping

    Returns:
        DataFrame: Sector-level aggregate KPI table
    """
    latest = ratios[ratios['year'] == ANALYSIS_YEAR].copy()

    for col in NUMERIC_COLS:
        if col in latest.columns:
            latest[col] = pd.to_numeric(latest[col], errors='coerce')

    sector_df = pd.merge(
        latest,
        sectors[['company_id', 'broad_sector', 'sub_sector']],
        on='company_id', how='left'
    )

    sector_agg = sector_df.groupby('broad_sector').agg(
        company_count       = ('company_id',              'count'),
        median_roe          = ('return_on_equity_pct',    'median'),
        median_roce         = ('return_on_capital_pct',   'median'),
        median_npm          = ('net_profit_margin_pct',   'median'),
        median_de           = ('debt_to_equity',          'median'),
        median_fcf          = ('free_cash_flow_cr',       'median'),
        median_rev_cagr_5yr = ('sales_cagr_5yr',         'median'),
        median_pat_cagr_5yr = ('net_profit_cagr_5yr',    'median'),
    ).round(2).reset_index()

    return sector_agg


# ── Database Saver ────────────────────────────────────────────────────────────

def save_sector_analytics(sector_agg):
    """
    Saves sector analytics table to SQLite database.

    Args:
        sector_agg: Sector aggregate DataFrame

    Returns:
        int: Number of rows saved
    """
    conn = sqlite3.connect(DB_PATH)
    sector_agg.to_sql(
        'sector_analytics', conn, if_exists='replace', index=False
    )
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sector_analytics")
    count = cursor.fetchone()[0]
    conn.close()

    print(f"sector_analytics table saved — {count} sectors")
    return count


# ── Master Runner ─────────────────────────────────────────────────────────────

def run_sector_analytics():
    """
    Master function — generates radar charts and computes
    sector-level aggregate KPIs.

    Returns:
        DataFrame: Sector analytics aggregate table

    Example:
        from src.analytics.sector_analytics import run_sector_analytics
        sector_agg = run_sector_analytics()
    """
    from src.etl.loader import load_all_data

    data        = load_all_data()
    sectors     = data['sectors']

    conn = sqlite3.connect(DB_PATH)
    ratios = pd.read_sql_query(
        "SELECT * FROM financial_ratios_computed", conn
    )
    peer_percentiles = pd.read_sql_query(
        "SELECT * FROM peer_percentiles", conn
    )
    conn.close()

    print("Generating radar charts...")
    generated, failed = generate_all_radar_charts(peer_percentiles)
    print(f"  Generated: {len(generated)} charts")
    print(f"  Failed:    {len(failed)}")

    print("\nComputing sector analytics...")
    sector_agg = compute_sector_analytics(ratios, sectors)

    print("\nSaving sector analytics to database...")
    save_sector_analytics(sector_agg)

    print("\nTop 3 sectors by median ROE:")
    print(sector_agg.nlargest(3, 'median_roe')[
        ['broad_sector', 'median_roe', 'company_count']
    ].to_string(index=False))

    return sector_agg


# ── Run directly for testing ──────────────────────────────────────────────────

if __name__ == "__main__":
    sector_agg = run_sector_analytics()
