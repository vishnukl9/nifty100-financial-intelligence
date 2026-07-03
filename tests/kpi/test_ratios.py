"""
test_ratios.py — Unit Tests for Financial Ratio Formulas
Tests all profitability, leverage and efficiency KPI functions.
"""

import sys
import os
import pytest
import pandas as pd
import numpy as np

project_path = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(project_path)
os.chdir(project_path)

from src.analytics.ratios import (
    compute_npm, compute_opm, compute_roe, compute_roce,
    compute_de_ratio, compute_icr, compute_net_debt,
    compute_asset_turnover
)


# ── Helper to build test DataFrames ──────────────────────────────────────────

def make_row(**kwargs):
    """Creates a single-row DataFrame for testing."""
    defaults = {
        'company_id':       'TEST',
        'year':             '2024-03',
        'sales':            1000.0,
        'net_profit':       100.0,
        'operating_profit': 200.0,
        'depreciation':     50.0,
        'other_income':     10.0,
        'interest':         20.0,
        'equity_capital':   100.0,
        'reserves':         400.0,
        'borrowings':       200.0,
        'total_assets':     800.0,
        'fixed_assets':     300.0,
        'investments':      50.0,
    }
    defaults.update(kwargs)
    defaults['total_equity'] = defaults['equity_capital'] + defaults['reserves']
    return pd.DataFrame([defaults])


# ── NPM Tests ─────────────────────────────────────────────────────────────────

def test_npm_normal():
    """NPM should be net_profit/sales * 100."""
    df = compute_npm(make_row(net_profit=100, sales=1000))
    assert df['net_profit_margin_pct'].iloc[0] == 10.0

def test_npm_zero_sales():
    """NPM should be NaN when sales is zero."""
    df = compute_npm(make_row(sales=0))
    assert pd.isna(df['net_profit_margin_pct'].iloc[0])

def test_npm_negative_profit():
    """NPM should be negative when company makes a loss."""
    df = compute_npm(make_row(net_profit=-50, sales=1000))
    assert df['net_profit_margin_pct'].iloc[0] == -5.0


# ── OPM Tests ─────────────────────────────────────────────────────────────────

def test_opm_normal():
    """OPM should be operating_profit/sales * 100."""
    df = compute_opm(make_row(operating_profit=250, sales=1000))
    assert df['operating_profit_margin_pct'].iloc[0] == 25.0

def test_opm_zero_sales():
    """OPM should be NaN when sales is zero."""
    df = compute_opm(make_row(sales=0))
    assert pd.isna(df['operating_profit_margin_pct'].iloc[0])


# ── ROE Tests ─────────────────────────────────────────────────────────────────

def test_roe_positive_equity():
    """ROE should be net_profit / (equity + reserves) * 100."""
    df = compute_roe(make_row(
        net_profit=100, equity_capital=100, reserves=400
    ))
    assert df['return_on_equity_pct'].iloc[0] == 20.0

def test_roe_negative_equity():
    """ROE should be None when equity is negative."""
    df = compute_roe(make_row(
        net_profit=100, equity_capital=10, reserves=-500
    ))
    assert pd.isna(df['return_on_equity_pct'].iloc[0])

def test_roe_zero_equity():
    """ROE should be None when total equity is zero."""
    df = compute_roe(make_row(
        net_profit=100, equity_capital=0, reserves=0
    ))
    assert pd.isna(df['return_on_equity_pct'].iloc[0])


# ── ROCE Tests ────────────────────────────────────────────────────────────────

def test_roce_normal():
    """ROCE = EBIT / capital_employed * 100."""
    df = compute_roce(make_row(
        operating_profit=200, depreciation=50,
        equity_capital=100, reserves=400, borrowings=200
    ))
    # EBIT = 200 - 50 = 150
    # Capital Employed = 500 + 200 = 700
    # ROCE = 150/700 * 100 = 21.43
    assert abs(df['return_on_capital_pct'].iloc[0] - 21.43) < 0.1

def test_roce_zero_capital():
    """ROCE should be None when capital employed is zero."""
    df = compute_roce(make_row(
        equity_capital=0, reserves=0, borrowings=0
    ))
    assert pd.isna(df['return_on_capital_pct'].iloc[0])


# ── D/E Tests ─────────────────────────────────────────────────────────────────

def test_de_normal():
    """D/E should be borrowings / total_equity."""
    df = compute_de_ratio(make_row(
        borrowings=500, equity_capital=100, reserves=400
    ))
    assert df['debt_to_equity'].iloc[0] == 1.0

def test_de_debt_free():
    """D/E should be 0 for debt-free companies."""
    df = compute_de_ratio(make_row(
        borrowings=0, equity_capital=100, reserves=400
    ))
    assert df['debt_to_equity'].iloc[0] == 0.0

def test_de_negative_equity():
    """D/E should be None when equity is negative."""
    df = compute_de_ratio(make_row(
        borrowings=200, equity_capital=10, reserves=-500
    ))
    assert pd.isna(df['debt_to_equity'].iloc[0])


# ── ICR Tests ─────────────────────────────────────────────────────────────────

def test_icr_normal():
    """ICR = (operating_profit + other_income) / interest."""
    df = compute_icr(make_row(
        operating_profit=200, other_income=10, interest=20
    ))
    assert df['interest_coverage'].iloc[0] == 10.5

def test_icr_debt_free():
    """ICR should be None when interest is zero (debt free)."""
    df = compute_icr(make_row(interest=0))
    assert pd.isna(df['interest_coverage'].iloc[0])


# ── Net Debt Tests ────────────────────────────────────────────────────────────

def test_net_debt_positive():
    """Net debt = borrowings - investments."""
    df = compute_net_debt(make_row(borrowings=500, investments=100))
    assert df['net_debt'].iloc[0] == 400.0

def test_net_debt_net_cash():
    """Net debt should be negative when investments exceed borrowings."""
    df = compute_net_debt(make_row(borrowings=100, investments=500))
    assert df['net_debt'].iloc[0] == -400.0


# ── Asset Turnover Tests ──────────────────────────────────────────────────────

def test_asset_turnover_normal():
    """Asset turnover = sales / total_assets."""
    df = compute_asset_turnover(make_row(sales=1000, total_assets=500))
    assert df['asset_turnover'].iloc[0] == 2.0

def test_asset_turnover_zero_assets():
    """Asset turnover should be NaN when total assets is zero."""
    df = compute_asset_turnover(make_row(total_assets=0))
    assert pd.isna(df['asset_turnover'].iloc[0])