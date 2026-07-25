from fastapi import APIRouter
import sqlite3
import os

router = APIRouter(tags=["valuation"])

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
DB_PATH = os.path.join(PROJECT_PATH, 'data', 'nifty100.db')

def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

@router.get("/market-cap/{ticker}")
def get_valuation_history(ticker: str):
    query = """
        SELECT year, price_to_earnings, price_to_book, ev_to_ebitda, dividend_yield_pct
        FROM market_cap
        WHERE company_id = ?
        ORDER BY year
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        cursor.execute(query, (ticker,))
        return cursor.fetchall()
