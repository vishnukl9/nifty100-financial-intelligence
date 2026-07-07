"""
health_score.py — Financial Health Scoring Module
Nifty 100 Financial Intelligence Platform
Sprint 3 — Screener & Health Scoring

Computes a composite Financial Health Score (0-100) for all 92
Nifty 100 companies using 4 weighted dimensions:

    Profitability (35%): ROE, ROCE, NPM
    Cash Quality  (30%): CFO Quality, FCF positive flag
    Growth        (20%): Revenue CAGR 5yr, PAT CAGR 5yr
    Leverage      (15%): D/E (inverted), ICR

Score Bands:
    80-100 = Excellent
    65-79  = Good
    50-64  = Average
    35-49  = Weak
    0-34   = Poor

Usage:
    from src.analytics.health_score import compute_health_score
    scored_df = compute_health_score(screener_df)
"""

import pandas as pd
import numpy as np
import os
import sys

# ── Path Configuration ────────────────────────────────────────────────────────

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(PROJECT_PATH)
os.chdir(PROJECT_PATH)


# ── Utility Functions ─────────────────────────────────────────────────────────

def winsorise(series, p_low=10, p_high=90):
    """
    Caps extreme values at P10 and P90 percentiles.
    Prevents outliers like BEL/HAL (4000%+ ROE) from
    distorting everyone else's scores.

    Args:
        series: Pandas Series of numeric values
        p_low:  Lower percentile cap (default 10)
        p_high: Upper percentile cap (default 90)

    Returns:
        Series: Winsorised values with extremes capped
    """
    low  = series.quantile(p_low / 100)
    high = series.quantile(p_high / 100)
    return series.clip(lower=low, upper=high)


def scale_to_100(series):
    """
    Scales a series to 0-100 range using min-max normalisation.
    After winsorisation, min maps to 0 and max maps to 100.

    Args:
        series: Pandas Series of numeric values

    Returns:
        Series: Values scaled to 0-100 range
    """
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return pd.Series([50.0] * len(series), index=series.index)
    return ((series - min_val) / (max_val - min_val) * 100).round(2)


def get_band(score):
    """
    Converts a numeric health score to a descriptive band label.

    Args:
        score: Numeric health score 0-100

    Returns:
        str: Band label
    """
    if score >= 80:   return 'Excellent'
    elif score >= 65: return 'Good'
    elif score >= 50: return 'Average'
    elif score >= 35: return 'Weak'
    else:             return 'Poor'


# ── Health Score Computer ─────────────────────────────────────────────────────

def compute_health_score(df):
    """
    Computes Financial Health Score (0-100) for all companies.

    Uses 4 weighted dimensions with P10/P90 winsorisation to
    handle extreme values before scaling.

    Dimension Weights:
        Profitability: 35% (ROE 15% + ROCE 10% + NPM 10%)
        Cash Quality:  30% (CFO Quality 10% + FCF flag 5% + buffer 15%)
        Growth:        20% (Revenue CAGR 10% + PAT CAGR 10%)
        Leverage:      15% (D/E inverted 10% + ICR 5%)

    Args:
        df: Screener DataFrame with all KPI columns

    Returns:
        DataFrame: Input DataFrame with health_score and
                   health_band columns added
    """
    df = df.copy()

    # Force all KPI columns to numeric (handles mixed-type columns)
    kpi_cols = [
        'return_on_equity_pct', 'return_on_capital_pct',
        'net_profit_margin_pct', 'cfo_quality_score',
        'free_cash_flow_cr', 'sales_cagr_5yr',
        'net_profit_cagr_5yr', 'debt_to_equity', 'interest_coverage'
    ]
    for col in kpi_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # ── Profitability Score (35%) ──────────────────────────────
    roe_w  = winsorise(df['return_on_equity_pct'].fillna(0))
    roce_w = winsorise(df['return_on_capital_pct'].fillna(0))
    npm_w  = winsorise(df['net_profit_margin_pct'].fillna(0))

    profitability_score = (
        scale_to_100(roe_w)  * 0.15 +
        scale_to_100(roce_w) * 0.10 +
        scale_to_100(npm_w)  * 0.10
    ) / 0.35 * 0.35

    # ── Cash Quality Score (30%) ───────────────────────────────
    cfo_w    = winsorise(df['cfo_quality_score'].fillna(0))
    fcf_flag = (df['free_cash_flow_cr'].fillna(0) > 0).astype(float) * 100

    cash_score = (
        scale_to_100(cfo_w) * 0.10 +
        fcf_flag            * 0.05
    ) / 0.15 * 0.30

    # ── Growth Score (20%) ─────────────────────────────────────
    rev_cagr_w = winsorise(df['sales_cagr_5yr'].fillna(0))
    pat_cagr_w = winsorise(df['net_profit_cagr_5yr'].fillna(0))

    growth_score = (
        scale_to_100(rev_cagr_w) * 0.10 +
        scale_to_100(pat_cagr_w) * 0.10
    ) / 0.20 * 0.20

    # ── Leverage Score (15%) ───────────────────────────────────
    # D/E: lower is better so we invert the scale
    de_median = df['debt_to_equity'].median()
    de_w      = winsorise(df['debt_to_equity'].fillna(de_median))
    de_score  = (100 - scale_to_100(de_w))

    icr_w     = winsorise(df['interest_coverage'].fillna(0))
    icr_score = scale_to_100(icr_w)

    leverage_score = (
        de_score  * 0.10 +
        icr_score * 0.05
    ) / 0.15 * 0.15

    # ── Composite Score ────────────────────────────────────────
    df['health_score'] = (
        profitability_score +
        cash_score +
        growth_score +
        leverage_score
    ).round(1)

    # Clip to valid range
    df['health_score'] = df['health_score'].clip(0, 100)

    # Add band label
    df['health_band'] = df['health_score'].apply(get_band)

    return df


# ── Excel Export ──────────────────────────────────────────────────────────────

def export_screener_excel(results, output_path='output/screener_output.xlsx'):
    """
    Exports all preset screener results to a colour-coded Excel file.
    One sheet per preset, sorted by health score descending.

    Green = health score >= 65 (Good or Excellent)
    Red   = health score < 50  (Weak or Poor)

    Args:
        results:     Dict of preset_name → filtered DataFrame
        output_path: Path to save the Excel file
    """
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill, Font, Alignment
    from openpyxl.utils.dataframe import dataframe_to_rows

    DISPLAY_COLS = [
        'company_id', 'broad_sector',
        'return_on_equity_pct', 'return_on_capital_pct',
        'net_profit_margin_pct', 'debt_to_equity',
        'interest_coverage', 'free_cash_flow_cr',
        'sales_cagr_5yr', 'net_profit_cagr_5yr',
        'pe_ratio', 'pb_ratio', 'dividend_yield_pct',
        'cfo_quality_score', 'asset_turnover',
        'health_score', 'health_band'
    ]

    GREEN  = PatternFill(
        start_color='C6EFCE', end_color='C6EFCE', fill_type='solid'
    )
    RED    = PatternFill(
        start_color='FFC7CE', end_color='FFC7CE', fill_type='solid'
    )
    HEADER = PatternFill(
        start_color='1F4E79', end_color='1F4E79', fill_type='solid'
    )

    wb = Workbook()
    wb.remove(wb.active)

    for preset_name, df in results.items():
        ws   = wb.create_sheet(title=preset_name[:31])
        cols = [c for c in DISPLAY_COLS if c in df.columns]
        df_display = df[cols].reset_index(drop=True)

        # Header row
        ws.append(cols)
        for cell in ws[1]:
            cell.fill      = HEADER
            cell.font      = Font(color='FFFFFF', bold=True)
            cell.alignment = Alignment(horizontal='center')

        # Data rows
        for row in dataframe_to_rows(df_display, index=False, header=False):
            ws.append(row)

        # Colour-code health score column
        if 'health_score' in cols:
            hs_col = cols.index('health_score') + 1
            for row_idx in range(2, ws.max_row + 1):
                cell  = ws.cell(row=row_idx, column=hs_col)
                score = cell.value
                if score is not None:
                    if score >= 65:
                        cell.fill = GREEN
                    elif score < 50:
                        cell.fill = RED

        # Auto-width columns
        for col in ws.columns:
            max_len = max(
                len(str(cell.value)) if cell.value else 0
                for cell in col
            )
            ws.column_dimensions[
                col[0].column_letter
            ].width = min(max_len + 2, 25)

    wb.save(output_path)
    print(f"Saved: {output_path}")
    print(f"Sheets: {wb.sheetnames}")


# ── Master Runner ─────────────────────────────────────────────────────────────

def run_health_scoring():
    """
    Master function — loads screener data, computes health scores,
    runs all presets and exports to Excel.

    Returns:
        tuple: (scored_df, results_dict)
    """
    from src.screener.engine import (
        load_screener_data, apply_filters, load_config
    )

    print("Loading screener data...")
    screener_df = load_screener_data()

    print("Computing health scores...")
    screener_df = compute_health_score(screener_df)

    print("\nHealth Score Distribution:")
    print(screener_df['health_band'].value_counts().to_string())

    print("\nRunning all presets...")
    config  = load_config()
    results = {}
    for preset_name, preset_config in config['presets'].items():
        filtered = apply_filters(screener_df, preset_config['filters'])
        filtered = filtered.sort_values('health_score', ascending=False)
        results[preset_name] = filtered
        print(f"  {preset_name:<25} → {len(filtered)} companies")

    print("\nExporting to Excel...")
    export_screener_excel(results)

    return screener_df, results


# ── Run directly for testing ──────────────────────────────────────────────────

if __name__ == "__main__":
    scored_df, results = run_health_scoring()

    print("\nTop 5 Healthiest Companies:")
    print(scored_df.nlargest(5, 'health_score')[
        ['company_id', 'broad_sector', 'health_score', 'health_band']
    ].to_string(index=False))
