from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
import sqlite3
import os
from typing import Optional

router = APIRouter(tags=["companies"])

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
DB_PATH = os.path.join(PROJECT_PATH, 'data', 'nifty100.db')
TEARSHEET_DIR = os.path.join(PROJECT_PATH, 'reports', 'tearsheets')

def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

@router.get("/companies")
def get_companies(
    sector: Optional[str] = None,
    market_cap_category: Optional[str] = None,
    search: Optional[str] = None
):
    query = """
        SELECT c.id, c.company_name, s.broad_sector, s.sub_sector, 
               r.return_on_equity_pct as roe_pct
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        LEFT JOIN (
            SELECT company_id, return_on_equity_pct
            FROM financial_ratios
            WHERE year = (SELECT MAX(year) FROM financial_ratios f2 WHERE f2.company_id = financial_ratios.company_id)
        ) r ON c.id = r.company_id
        WHERE 1=1
    """
    params = []
    
    if sector:
        query += " AND s.broad_sector = ?"
        params.append(sector)
    if search:
        query += " AND (c.company_name LIKE ? OR c.id LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
        
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        
    return results

@router.get("/companies/{ticker}")
def get_company_profile(ticker: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM companies WHERE id = ?", (ticker,))
        company = cursor.fetchone()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
            
        cursor.execute("SELECT * FROM sectors WHERE company_id = ?", (ticker,))
        sector = cursor.fetchone()
        
        cursor.execute("SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year DESC LIMIT 1", (ticker,))
        kpis = cursor.fetchone()
        
    return {
        "company": company,
        "sector": sector,
        "latest_kpis": kpis
    }

@router.get("/companies/{ticker}/pl")
def get_company_pl(ticker: str, from_year: Optional[str] = None, to_year: Optional[str] = None):
    query = "SELECT * FROM profitandloss WHERE company_id = ?"
    params = [ticker]
    # In a real app we'd parse YYYY-MM and filter by year.
    query += " ORDER BY year"
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

@router.get("/companies/{ticker}/bs")
def get_company_bs(ticker: str, from_year: Optional[str] = None, to_year: Optional[str] = None):
    query = "SELECT * FROM balancesheet WHERE company_id = ? ORDER BY year"
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        cursor.execute(query, [ticker])
        return cursor.fetchall()

@router.get("/companies/{ticker}/cashflow")
def get_company_cf(ticker: str, from_year: Optional[str] = None, to_year: Optional[str] = None):
    query = "SELECT * FROM cashflow WHERE company_id = ? ORDER BY year"
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        cursor.execute(query, [ticker])
        return cursor.fetchall()

@router.get("/companies/{ticker}/ratios")
def get_company_ratios(ticker: str, year: Optional[int] = None):
    query = "SELECT * FROM financial_ratios WHERE company_id = ?"
    params = [ticker]
    if year:
        query += " AND year = ?"
        params.append(year)
    query += " ORDER BY year"
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

@router.get("/companies/{ticker}/tearsheet")
def get_company_tearsheet(ticker: str):
    file_path = os.path.join(TEARSHEET_DIR, f"{ticker}_tearsheet.pdf")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Tearsheet not found for this company")
    return FileResponse(file_path, media_type="application/pdf", filename=f"{ticker}_tearsheet.pdf")
