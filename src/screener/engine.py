"""
engine.py — Investment Screener Filter Engine
Nifty 100 Financial Intelligence Platform
Sprint 3 — Screener & Health Scoring

This module implements the investment screener with 15 filterable
metrics and 6 preset templates. Filters are loaded from
config/screener_config.yaml so analysts can adjust thresholds
without touching any Python code.

Special Rules:
    - D/E filter automatically skips Financials sector companies
    - ICR filter treats debt-free companies as ICR = infinity
    - sales_min filter maps to the sales column from P&L

Usage:
    from src.screener.engine import run_screener, run_all_presets
    results = run_all_presets()
"""

import pandas as pd
import numpy as np
import sqlite3
import yaml
import os
import sys

# ── Path Configuration ────────────────────────────────────────────────────────

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(PROJECT_PATH)
os.chdir(PROJECT_PATH)

DB_PATH          = 'data/nifty100.db'
CONFIG_PATH      = 'config/screener_config.yaml'
ANALYSIS_YEAR    = '2024-03'
MARKET_CAP_YEAR  = 2024


# ── Data Loader ───────────────────────────────────────────────────────────────

def load_screener_data():
    """
    Loads and merges all data needed for screening:
    - financial_ratios_computed (latest year)
    - market_cap (P/E, P/B, dividend yield)
    - profitandloss (sales column)
    - sectors (broad_sector, sub_sector)

    Returns:
        DataFrame: Master screener DataFrame with all filterable columns
    """
    from src.etl.loader import load_all_data

    conn   = sqlite3.connect(DB_PATH)
    ratios = pd.read_sql_query(
        "SELECT * FROM financial_ratios_computed", conn
    )
    conn.close()

    data       = load_all_data()
    market_cap = data['market_cap']
    sectors    = data['sectors']
    pl         = data['profitandloss']

    # Latest ratios
    latest_ratios = ratios[ratios['year'] == ANALYSIS_YEAR].copy()

    # Latest market cap
    latest_mc = market_cap[market_cap['year'] == MARKET_CAP_YEAR][[
        'company_id', 'market_cap_crore', 'pe_ratio',
        'pb_ratio', 'dividend_yield_pct'
    ]]

    # Latest sales
    latest_pl = pl[pl['year'] == ANALYSIS_YEAR][['company_id', 'sales']]

    # Merge all
    df = pd.merge(latest_ratios, latest_mc, on='company_id', how='left')
    df = pd.merge(df, latest_pl,            on='company_id', how='left')
    df = pd.merge(
        df,
        sectors[['company_id', 'broad_sector', 'sub_sector']],
        on='company_id', how='left'
    )

    return df


# ── Config Loader ─────────────────────────────────────────────────────────────

def load_config():
    """
    Loads screener thresholds from screener_config.yaml.

    Returns:
        dict: Full config dictionary with all presets
    """
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)


# ── Core Filter Engine ────────────────────────────────────────────────────────

def apply_filters(df, filters, broad_sector_col='broad_sector'):
    """
    Applies threshold filters to the screener DataFrame.

    Supported filter key suffixes:
        _min  → column value must be >= threshold
        _max  → column value must be <= threshold

    Special Rules:
        debt_to_equity_* → Financials sector companies are skipped
                           (their D/E is structurally high due to deposits)
        sales_min        → maps to 'sales' column from P&L

    Args:
        df:               Master screener DataFrame
        filters:          Dict of filter_key: threshold from config
        broad_sector_col: Column name for sector classification

    Returns:
        DataFrame: Filtered subset of input DataFrame
    """
    df   = df.copy()
    mask = pd.Series([True] * len(df), index=df.index)

    for filter_key, threshold in filters.items():

        # Map sales_min → sales column
        if filter_key == 'sales_min':
            col = 'sales'
            mask &= df[col].fillna(0) >= threshold
            continue

        # Parse column name and direction
        if filter_key.endswith('_min'):
            col       = filter_key[:-4]
            direction = 'min'
        elif filter_key.endswith('_max'):
            col       = filter_key[:-4]
            direction = 'max'
        else:
            continue

        # Skip if column not in DataFrame
        if col not in df.columns:
            print(f"  Warning: column '{col}' not found — skipping filter")
            continue

        # Special rule: skip Financials sector for D/E filter
        if col == 'debt_to_equity':
            is_financial = df[broad_sector_col] == 'Financials'
            if direction == 'min':
                mask &= is_financial | (df[col].fillna(0) >= threshold)
            else:
                mask &= is_financial | (df[col].fillna(999) <= threshold)
            continue

        # Apply standard filter
        if direction == 'min':
            mask &= df[col].fillna(-999) >= threshold
        else:
            mask &= df[col].fillna(999) <= threshold

    return df[mask].copy()


# ── Single Preset Runner ──────────────────────────────────────────────────────

def run_screener(preset_name, screener_df=None):
    """
    Runs a single named preset screener.

    Args:
        preset_name:  Name of preset from screener_config.yaml
        screener_df:  Optional pre-loaded screener DataFrame.
                      If None, loads fresh from database.

    Returns:
        DataFrame: Filtered and sorted results for the preset

    Example:
        from src.screener.engine import run_screener
        results = run_screener('quality_compounder')
    """
    config  = load_config()
    presets = config['presets']

    if preset_name not in presets:
        raise ValueError(
            f"Preset '{preset_name}' not found. "
            f"Available: {list(presets.keys())}"
        )

    if screener_df is None:
        screener_df = load_screener_data()

    preset_config = presets[preset_name]
    filters       = preset_config['filters']
    rank_col      = preset_config['rank_by']

    filtered = apply_filters(screener_df, filters)

    if rank_col in filtered.columns:
        filtered = filtered.sort_values(rank_col, ascending=False)

    return filtered


# ── All Presets Runner ────────────────────────────────────────────────────────

def run_all_presets():
    """
    Runs all 6 preset screeners and returns results as a dictionary.

    Returns:
        dict: preset_name → filtered DataFrame

    Example:
        from src.screener.engine import run_all_presets
        results = run_all_presets()
        quality = results['quality_compounder']
    """
    config      = load_config()
    presets     = config['presets']
    screener_df = load_screener_data()

    results = {}

    print("Running 6 preset screeners:")
    print(f"  {'Preset':<25} {'Companies Found':>16}")
    print(f"  {'-'*42}")

    for preset_name, preset_config in presets.items():
        filters  = preset_config['filters']
        rank_col = preset_config['rank_by']

        filtered = apply_filters(screener_df, filters)

        if rank_col in filtered.columns:
            filtered = filtered.sort_values(rank_col, ascending=False)

        results[preset_name] = filtered
        status = "✅" if 5 <= len(filtered) <= 50 else "⚠️ "
        print(f"  {status} {preset_name:<25} → {len(filtered)} companies")

    return results


# ── Run directly for testing ──────────────────────────────────────────────────

if __name__ == "__main__":
    results = run_all_presets()

    print("\nQuality Compounder — Top 5:")
    qc = results['quality_compounder']
    print(qc[['company_id', 'broad_sector',
               'return_on_equity_pct', 'debt_to_equity',
               'free_cash_flow_cr']].head(5).to_string(index=False))
