"""
loader.py — Data Loading & Cleaning Module
Nifty 100 Financial Intelligence Platform
Sprint 1 — Data Foundation

This module loads all core Excel files, normalises year formats
and company tickers, removes TTM rows, and returns clean DataFrames
ready for database loading in the next step.

Usage:
    from src.etl.loader import load_all_data
    pl, bs, cf, companies, analysis, documents, prosandcons = load_all_data()
"""

import pandas as pd
import re
import os

# ── Path Configuration ────────────────────────────────────────────────────────

RAW_DIR        = "data/raw"
SUPPORTING_DIR = "data/supporting"

CORE_FILES = {
    "profitandloss": os.path.join(RAW_DIR, "profitandloss.xlsx"),
    "balancesheet":  os.path.join(RAW_DIR, "balancesheet.xlsx"),
    "cashflow":      os.path.join(RAW_DIR, "cashflow.xlsx"),
    "companies":     os.path.join(RAW_DIR, "companies.xlsx"),
    "analysis":      os.path.join(RAW_DIR, "analysis.xlsx"),
    "documents":     os.path.join(RAW_DIR, "documents.xlsx"),
    "prosandcons":   os.path.join(RAW_DIR, "prosandcons.xlsx"),
}

SUPPORTING_FILES = {
    "sectors":          os.path.join(SUPPORTING_DIR, "sectors.xlsx"),
    "stock_prices":     os.path.join(SUPPORTING_DIR, "stock_prices.xlsx"),
    "market_cap":       os.path.join(SUPPORTING_DIR, "market_cap.xlsx"),
    "financial_ratios": os.path.join(SUPPORTING_DIR, "financial_ratios.xlsx"),
    "peer_groups":      os.path.join(SUPPORTING_DIR, "peer_groups.xlsx"),
}

# ── Normaliser Functions ──────────────────────────────────────────────────────

def normalize_year(year_str):
    """
    Converts messy year strings into clean YYYY-MM format.

    Examples:
        'Mar 2024' → '2024-03'
        'Dec 2022' → '2022-12'
        'TTM'      → None  (row will be dropped)
        None       → None  (row will be dropped)

    Args:
        year_str: Raw year value from Excel file

    Returns:
        str: Cleaned year in 'YYYY-MM' format, or None if invalid
    """
    if pd.isna(year_str):
        return None

    year_str = str(year_str).strip()

    # Discard TTM (Trailing Twelve Months) rows
    if year_str == "TTM":
        return None

    # Month name to number mapping
    month_map = {
        "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
        "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
        "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
    }

    # Match formats like 'Mar 2024' or 'Dec 2022'
    match = re.match(r"([A-Za-z]{3})\s(\d{4})", year_str)
    if match:
        month = match.group(1).capitalize()
        year  = match.group(2)
        return f"{year}-{month_map.get(month, '01')}"

    return None


def normalize_ticker(ticker):
    """
    Cleans company ID (NSE ticker) to uppercase stripped format.

    Examples:
        ' tcs '     → 'TCS'
        'infy'      → 'INFY'
        'BAJAJ-AUTO'→ 'BAJAJ-AUTO'

    Args:
        ticker: Raw company ID value from Excel file

    Returns:
        str: Cleaned uppercase ticker, or None if invalid
    """
    if pd.isna(ticker):
        return None
    return str(ticker).strip().upper()


# ── Core Cleaning Function ────────────────────────────────────────────────────

def clean_dataframe(df):
    """
    Applies year and ticker normalisation to a DataFrame.
    - Normalises company_id column if present
    - Normalises year column if present
    - Drops TTM and unparseable year rows
    - Removes duplicate (company_id, year) pairs — keeps last

    Args:
        df: Raw pandas DataFrame loaded from Excel

    Returns:
        DataFrame: Cleaned and deduplicated DataFrame
    """
    if "company_id" in df.columns:
        df["company_id"] = df["company_id"].apply(normalize_ticker)

    if "year" in df.columns:
        df["year"] = df["year"].apply(normalize_year)
        df = df.dropna(subset=["year"])
        df = df.drop_duplicates(subset=["company_id", "year"], keep="last")

    return df.reset_index(drop=True)


# ── Individual File Loaders ───────────────────────────────────────────────────

def load_profit_and_loss():
    """Load and clean the Profit & Loss dataset."""
    df = pd.read_excel(CORE_FILES["profitandloss"], header=1)
    return clean_dataframe(df)


def load_balance_sheet():
    """Load and clean the Balance Sheet dataset."""
    df = pd.read_excel(CORE_FILES["balancesheet"], header=1)
    return clean_dataframe(df)


def load_cash_flow():
    """Load and clean the Cash Flow dataset."""
    df = pd.read_excel(CORE_FILES["cashflow"], header=1)
    return clean_dataframe(df)


def load_companies():
    """Load and clean the Companies master dataset."""
    df = pd.read_excel(CORE_FILES["companies"], header=1)
    df["id"] = df["id"].apply(normalize_ticker)
    return df


def load_analysis():
    """Load and clean the Analysis dataset (partial coverage ~8 companies)."""
    df = pd.read_excel(CORE_FILES["analysis"], header=1)
    if "company_id" in df.columns:
        df["company_id"] = df["company_id"].apply(normalize_ticker)
    return df


def load_documents():
    """Load and clean the Documents (Annual Reports) dataset."""
    df = pd.read_excel(CORE_FILES["documents"], header=1)
    if "company_id" in df.columns:
        df["company_id"] = df["company_id"].apply(normalize_ticker)
    return df


def load_prosandcons():
    """Load and clean the Pros & Cons dataset (partial coverage ~8 companies)."""
    df = pd.read_excel(CORE_FILES["prosandcons"], header=1)
    if "company_id" in df.columns:
        df["company_id"] = df["company_id"].apply(normalize_ticker)
    return df


def load_sectors():
    """Load and clean the Sectors mapping dataset."""
    df = pd.read_excel(SUPPORTING_FILES["sectors"], header=0)
    if "company_id" in df.columns:
        df["company_id"] = df["company_id"].apply(normalize_ticker)
    return df


def load_market_cap():
    """Load and clean the Market Cap dataset."""
    df = pd.read_excel(SUPPORTING_FILES["market_cap"], header=0)
    if "company_id" in df.columns:
        df["company_id"] = df["company_id"].apply(normalize_ticker)
    return df


def load_financial_ratios():
    """Load and clean the Financial Ratios dataset."""
    df = pd.read_excel(SUPPORTING_FILES["financial_ratios"], header=0)
    if "company_id" in df.columns:
        df["company_id"] = df["company_id"].apply(normalize_ticker)
    return df


def load_peer_groups():
    """Load and clean the Peer Groups dataset."""
    df = pd.read_excel(SUPPORTING_FILES["peer_groups"], header=0)
    if "company_id" in df.columns:
        df["company_id"] = df["company_id"].apply(normalize_ticker)
    return df


# ── Master Loader ─────────────────────────────────────────────────────────────

def load_all_data():
    """
    Loads and cleans all 12 datasets (7 core + 5 supporting).

    Returns:
        dict: Dictionary with dataset names as keys and clean
              DataFrames as values.

    Example:
        data = load_all_data()
        pl   = data['profitandloss']
        bs   = data['balancesheet']
    """
    print("Loading all datasets...")

    data = {
        "profitandloss":    load_profit_and_loss(),
        "balancesheet":     load_balance_sheet(),
        "cashflow":         load_cash_flow(),
        "companies":        load_companies(),
        "analysis":         load_analysis(),
        "documents":        load_documents(),
        "prosandcons":      load_prosandcons(),
        "sectors":          load_sectors(),
        "market_cap":       load_market_cap(),
        "financial_ratios": load_financial_ratios(),
        "peer_groups":      load_peer_groups(),
    }

    print("\nDataset Summary:")
    print(f"  {'Dataset':<20} {'Rows':>6}  {'Cols':>5}")
    print(f"  {'-'*35}")
    for name, df in data.items():
        print(f"  {name:<20} {df.shape[0]:>6}  {df.shape[1]:>5}")

    print("\nAll datasets loaded and cleaned successfully!")
    return data


# ── Run directly for testing ──────────────────────────────────────────────────

if __name__ == "__main__":
    data = load_all_data()
