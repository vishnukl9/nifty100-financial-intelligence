import sqlite3
import pandas as pd
import os

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
DB_PATH = os.path.join(PROJECT_PATH, 'data', 'nifty100.db')

def test_sales_positive():
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("SELECT sales FROM profitandloss", conn)
        assert (df['sales'].fillna(0) >= 0).all(), "Found negative sales"

def test_total_assets_eq_liabilities():
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("SELECT total_assets, total_liabilities FROM balancesheet", conn)
        # Check if assets == liabilities within a tolerance of 10 crores
        # (some minor rounding differences exist in reported data)
        diff = abs(df['total_assets'].fillna(0) - df['total_liabilities'].fillna(0))
        assert (diff < 10).all(), "Total assets != Total liabilities"

def test_no_duplicate_ratios():
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("SELECT company_id, year FROM financial_ratios", conn)
        duplicates = df.duplicated(subset=['company_id', 'year'])
        assert not duplicates.any(), "Found duplicate ratio entries"
