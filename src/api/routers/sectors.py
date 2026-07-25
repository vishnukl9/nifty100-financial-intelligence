from fastapi import APIRouter, HTTPException
import sqlite3
import os

router = APIRouter(tags=["sectors"])

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
DB_PATH = os.path.join(PROJECT_PATH, 'data', 'nifty100.db')

def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

@router.get("/sectors")
def get_sectors():
    query = """
        SELECT s.broad_sector, COUNT(c.id) as company_count,
               AVG(r.return_on_equity_pct) as median_roe,
               AVG(m.price_to_earnings) as median_pe,
               AVG(r.debt_to_equity) as median_de
        FROM sectors s
        JOIN companies c ON s.company_id = c.id
        LEFT JOIN (
            SELECT company_id, return_on_equity_pct, debt_to_equity
            FROM financial_ratios
            WHERE year = (SELECT MAX(year) FROM financial_ratios f2 WHERE f2.company_id = financial_ratios.company_id)
        ) r ON c.id = r.company_id
        LEFT JOIN (
            SELECT company_id, price_to_earnings
            FROM market_cap
            WHERE year = (SELECT MAX(year) FROM market_cap m2 WHERE m2.company_id = market_cap.company_id)
        ) m ON c.id = m.company_id
        GROUP BY s.broad_sector
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

@router.get("/sectors/{sector}/companies")
def get_sector_companies(sector: str):
    query = """
        SELECT c.id, c.company_name, r.*
        FROM companies c
        JOIN sectors s ON c.id = s.company_id
        LEFT JOIN (
            SELECT *
            FROM financial_ratios
            WHERE year = (SELECT MAX(year) FROM financial_ratios f2 WHERE f2.company_id = financial_ratios.company_id)
        ) r ON c.id = r.company_id
        WHERE s.broad_sector = ?
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        cursor.execute(query, (sector,))
        results = cursor.fetchall()
        
    if not results:
        raise HTTPException(status_code=404, detail="Sector not found or has no companies")
    return results
