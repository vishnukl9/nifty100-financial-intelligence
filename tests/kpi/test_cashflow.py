"""
test_cashflow.py — Unit Tests for Cash Flow KPI Functions
"""

import sys
import os
import pytest
import pandas as pd
import numpy as np

project_path = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(project_path)
os.chdir(project_path)

from src.analytics.cashflow_kpis import (
    compute_fcf, compute_cfo_quality,
    compute_capex_intensity, get_capital_allocation_pattern
)


def make_cf_row(**kwargs):
    """Creates a single-row DataFrame for cash flow testing."""
    defaults = {
        'company_id':          'TEST',
        'year':                '2024-03',
        'operating_activity':  500.0,
        'investing_activity': -200.0,
        'financing_activity': -100.0,
        'net_cash_flow':       200.0,
        'sales':              1000.0,
        'net_profit':          200.0,
        'operating_profit':    300.0,
    }
    defaults.update(kwargs)
    return pd.DataFrame([defaults])


# ── FCF Tests ─────────────────────────────────────────────────────────────────

def test_fcf_positive():
    """FCF should be CFO + CFI."""
    df = compute_fcf(make_cf_row(
        operating_activity=500, investing_activity=-200
    ))
    assert df['free_cash_flow_cr'].iloc[0] == 300.0

def test_fcf_negative():
    """FCF can be negative when investing outflows exceed CFO."""
    df = compute_fcf(make_cf_row(
        operating_activity=100, investing_activity=-500
    ))
    assert df['free_cash_flow_cr'].iloc[0] == -400.0


# ── CFO Quality Tests ─────────────────────────────────────────────────────────

def test_cfo_quality_high():
    """CFO quality > 1.0 should be labelled High Quality."""
    df = compute_cfo_quality(make_cf_row(
        operating_activity=300, net_profit=200
    ))
    assert df['cfo_quality_label'].iloc[0] == 'High Quality'

def test_cfo_quality_moderate():
    """CFO quality between 0.5 and 1.0 should be Moderate."""
    df = compute_cfo_quality(make_cf_row(
        operating_activity=150, net_profit=200
    ))
    assert df['cfo_quality_label'].iloc[0] == 'Moderate'

def test_cfo_quality_accrual_risk():
    """CFO quality < 0.5 should be Accrual Risk."""
    df = compute_cfo_quality(make_cf_row(
        operating_activity=50, net_profit=200
    ))
    assert df['cfo_quality_label'].iloc[0] == 'Accrual Risk'

def test_cfo_quality_zero_profit():
    """CFO quality should be NaN when net profit is zero."""
    df = compute_cfo_quality(make_cf_row(net_profit=0))
    assert pd.isna(df['cfo_quality_score'].iloc[0])


# ── CapEx Intensity Tests ─────────────────────────────────────────────────────

def test_capex_asset_light():
    """CapEx intensity < 3% should be Asset Light."""
    df = compute_capex_intensity(make_cf_row(
        investing_activity=-20, sales=1000
    ))
    assert df['capex_label'].iloc[0] == 'Asset Light'

def test_capex_intensive():
    """CapEx intensity > 8% should be Capital Intensive."""
    df = compute_capex_intensity(make_cf_row(
        investing_activity=-100, sales=1000
    ))
    assert df['capex_label'].iloc[0] == 'Capital Intensive'


# ── Capital Allocation Pattern Tests ─────────────────────────────────────────

def test_pattern_reinvestor():
    """(+,-,-) pattern should be Reinvestor."""
    pattern, label = get_capital_allocation_pattern(500, -200, -100)
    assert label == 'Reinvestor'

def test_pattern_distress():
    """(-,-,+) pattern should be Distress Signal."""
    pattern, label = get_capital_allocation_pattern(-200, -100, 500)
    assert label == 'Distress Signal'

def test_pattern_asset_seller():
    """(+,+,-) pattern should be Asset Seller."""
    pattern, label = get_capital_allocation_pattern(500, 200, -100)
    assert label == 'Asset Seller'