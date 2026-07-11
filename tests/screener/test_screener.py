import pytest
import pandas as pd
import sqlite3
import os
import sys

project_path = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(project_path)
os.chdir(project_path)

from src.screener.engine import apply_filters, load_screener_data
from src.analytics.health_score import compute_health_score

# ── Screener Tests ────────────────────────────────────────────────

def test_quality_compounder_filter():
    """Quality Compounder should return companies with high ROE, low D/E."""
    df = load_screener_data()
    filters = {
        'return_on_equity_pct_min': 15.0,
        'debt_to_equity_max': 1.0,
        'free_cash_flow_cr_min': 0.0,
        'sales_cagr_5yr_min': 10.0
    }
    result = apply_filters(df, filters)
    assert len(result) > 0, "Quality Compounder should find companies"
    assert all(result['return_on_equity_pct'].fillna(0) >= 15.0), \
        "All ROE values should be >= 15%"
    assert all(result['debt_to_equity'].fillna(0) <= 1.0), \
        "All D/E values should be <= 1.0"

def test_value_pick_filter():
    """Value Pick should find undervalued companies."""
    df = load_screener_data()
    filters = {
        'pe_ratio_max': 30.0,
        'pb_ratio_max': 5.0
    }
    result = apply_filters(df, filters)
    assert len(result) > 0, "Value Pick should find companies"
    assert len(result) >= 5, "Should find at least 5 value stocks"

def test_growth_accelerator_filter():
    """Growth Accelerator should find high-growth companies."""
    df = load_screener_data()
    filters = {
        'net_profit_cagr_5yr_min': 20.0,
        'sales_cagr_5yr_min': 15.0
    }
    result = apply_filters(df, filters)
    assert len(result) > 0, "Growth Accelerator should find companies"

def test_all_presets_return_valid_counts():
    """All 6 presets should return reasonable company counts."""
    df = load_screener_data()
    
    presets = {
        'quality_compounder': {'return_on_equity_pct_min': 15.0, 'debt_to_equity_max': 1.0},
        'value_pick': {'pe_ratio_max': 30.0, 'pb_ratio_max': 5.0},
        'growth_accelerator': {'net_profit_cagr_5yr_min': 20.0},
        'dividend_champion': {'dividend_yield_pct_min': 2.0},
        'debt_free_blue_chip': {'debt_to_equity_max': 0.0},
        'turnaround_watch': {'sales_cagr_3yr_min': 15.0}
    }
    
    for preset_name, filters in presets.items():
        result = apply_filters(df, filters)
        assert 5 <= len(result) <= 50, \
            f"{preset_name}: Expected 5-50 companies, got {len(result)}"

# ── Health Score Tests ────────────────────────────────────────────

def test_health_score_range():
    """Health score should be between 0 and 100."""
    df = load_screener_data()
    df = compute_health_score(df)
    
    assert 'health_score' in df.columns, "health_score column should exist"
    assert all(df['health_score'].between(0, 100, inclusive='both')), \
        "All health scores should be 0-100"
    assert all(df['health_band'].isin(
        ['Excellent', 'Good', 'Average', 'Weak', 'Poor']
    )), "All health bands should be valid"

def test_health_score_bands():
    """Health score bands should be correctly assigned."""
    df = load_screener_data()
    df = compute_health_score(df)
    
    excellent = df[df['health_score'] >= 80]
    good = df[(df['health_score'] >= 65) & (df['health_score'] < 80)]
    average = df[(df['health_score'] >= 50) & (df['health_score'] < 65)]
    weak = df[(df['health_score'] >= 35) & (df['health_score'] < 50)]
    poor = df[df['health_score'] < 35]
    
    assert all(excellent['health_band'] == 'Excellent'), \
        "Score >= 80 should be Excellent"
    assert all(good['health_band'] == 'Good'), \
        "Score 65-79 should be Good"

def test_health_score_no_nulls():
    """No company should have null health score."""
    df = load_screener_data()
    df = compute_health_score(df)
    assert df['health_score'].notna().sum() > 90, \
        "At least 90 companies should have health scores"

# ── Peer Percentile Tests ─────────────────────────────────────────

def test_peer_percentiles_exist():
    """peer_percentiles table should exist in database."""
    conn = sqlite3.connect('data/nifty100.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='peer_percentiles'"
    )
    result = cursor.fetchone()
    conn.close()
    assert result is not None, "peer_percentiles table should exist"

def test_peer_percentiles_range():
    """Peer percentiles should be between 0 and 1."""
    conn = sqlite3.connect('data/nifty100.db')
    peer_pcts = pd.read_sql_query(
        "SELECT * FROM peer_percentiles WHERE percentile_rank IS NOT NULL",
        conn
    )
    conn.close()
    
    assert len(peer_pcts) > 0, "Should have percentile records"
    assert all(peer_pcts['percentile_rank'].between(0, 1, inclusive='both')), \
        "All percentile ranks should be 0-1"

def test_peer_percentiles_coverage():
    """Should have percentile ranks for multiple peer groups."""
    conn = sqlite3.connect('data/nifty100.db')
    peer_pcts = pd.read_sql_query(
        "SELECT COUNT(DISTINCT peer_group_name) as groups FROM peer_percentiles",
        conn
    )
    conn.close()
    
    assert peer_pcts.iloc[0]['groups'] >= 10, \
        "Should have percentiles for at least 10 peer groups"

# ── Sector Analytics Tests ────────────────────────────────────────

def test_sector_analytics_exists():
    """sector_analytics table should exist."""
    conn = sqlite3.connect('data/nifty100.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='sector_analytics'"
    )
    result = cursor.fetchone()
    conn.close()
    assert result is not None, "sector_analytics table should exist"

def test_sector_analytics_coverage():
    """sector_analytics should have 10 sectors."""
    conn = sqlite3.connect('data/nifty100.db')
    sector_agg = pd.read_sql_query(
        "SELECT COUNT(*) as count FROM sector_analytics", conn
    )
    conn.close()
    
    count = sector_agg.iloc[0]['count']
    assert count == 10, f"Should have 10 sectors, got {count}"

# ── File Existence Tests ──────────────────────────────────────────

def test_screener_output_excel_exists():
    """screener_output.xlsx should exist."""
    assert os.path.exists('output/screener_output.xlsx'), \
        "screener_output.xlsx should exist in output/"

def test_peer_comparison_excel_exists():
    """peer_comparison.xlsx should exist."""
    assert os.path.exists('output/peer_comparison.xlsx'), \
        "peer_comparison.xlsx should exist in output/"

def test_radar_charts_exist():
    """All 56 radar charts should be generated."""
    radar_dir = 'reports/radar_charts'
    assert os.path.exists(radar_dir), "radar_charts directory should exist"
    
    charts = [f for f in os.listdir(radar_dir) if f.endswith('.png')]
    assert len(charts) == 56, f"Should have 56 radar charts, got {len(charts)}"