import streamlit as st
import pandas as pd
import sqlite3
import os
import sys

project_path = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(project_path)
os.chdir(project_path)

DB_PATH = 'data/nifty100.db'

@st.cache_data(ttl=600)
def get_companies():
    """Load companies master data."""
    from src.etl.loader import load_all_data
    data = load_all_data()
    return data['companies']

@st.cache_data(ttl=600)
def get_ratios(ticker=None, year=None):
    """Load financial ratios."""
    conn = sqlite3.connect(DB_PATH)
    if ticker and year:
        query = f"SELECT * FROM financial_ratios_computed WHERE company_id = '{ticker}' AND year = '{year}'"
    elif ticker:
        query = f"SELECT * FROM financial_ratios_computed WHERE company_id = '{ticker}'"
    elif year:
        query = f"SELECT * FROM financial_ratios_computed WHERE year = '{year}'"
    else:
        query = "SELECT * FROM financial_ratios_computed"
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

@st.cache_data(ttl=600)
def get_sectors():
    """Load sector mapping."""
    from src.etl.loader import load_all_data
    data = load_all_data()
    return data['sectors']

@st.cache_data(ttl=600)
def get_sector_analytics():
    """Load sector aggregates."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM sector_analytics", conn)
    conn.close()
    return df

@st.cache_data(ttl=600)
def get_health_scores():
    """Load health scores (from ratios table)."""
    ratios = get_ratios()
    return ratios[['company_id', 'health_score', 'health_band']].drop_duplicates()

print("✅ Data loader ready!")