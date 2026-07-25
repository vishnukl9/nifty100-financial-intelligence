from fastapi import APIRouter, HTTPException, Query
import sqlite3
import os
from typing import Optional

router = APIRouter(tags=["screener"])

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
DB_PATH = os.path.join(PROJECT_PATH, 'data', 'nifty100.db')

def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

@router.get("/screener")
def run_screener(
    min_roe: Optional[float] = None,
    max_de: Optional[float] = None,
    min_fcf: Optional[float] = None,
    sector: Optional[str] = None,
    min_rev_cagr_5yr: Optional[float] = None,
    min_pat_cagr_5yr: Optional[float] = None,
    max_pe: Optional[float] = None
):
    query = """
        SELECT c.id, c.company_name, s.broad_sector, 
               r.return_on_equity_pct as roe, r.debt_to_equity as de, r.free_cash_flow_cr as fcf,
               m.price_to_earnings as pe
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        LEFT JOIN (
            SELECT company_id, return_on_equity_pct, debt_to_equity, free_cash_flow_cr
            FROM financial_ratios
            WHERE year = (SELECT MAX(year) FROM financial_ratios f2 WHERE f2.company_id = financial_ratios.company_id)
        ) r ON c.id = r.company_id
        LEFT JOIN (
            SELECT company_id, price_to_earnings
            FROM market_cap
            WHERE year = (SELECT MAX(year) FROM market_cap m2 WHERE m2.company_id = market_cap.company_id)
        ) m ON c.id = m.company_id
        WHERE 1=1
    """
    params = []
    
    if min_roe is not None:
        query += " AND r.return_on_equity_pct >= ?"
        params.append(min_roe)
    if max_de is not None:
        query += " AND r.debt_to_equity <= ?"
        params.append(max_de)
    if min_fcf is not None:
        query += " AND r.free_cash_flow_cr >= ?"
        params.append(min_fcf)
    if sector:
        query += " AND s.broad_sector = ?"
        params.append(sector)
    if max_pe is not None:
        query += " AND m.price_to_earnings <= ?"
        params.append(max_pe)
        
    # Ignore CAGR for now as it needs a join with the cagr output which we might not have in sqlite
    # Alternatively we can add cagr to sqlite or just not fully filter on them in SQL
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = dict_factory
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter values: {str(e)}")
