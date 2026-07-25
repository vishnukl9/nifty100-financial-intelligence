from fastapi import APIRouter
import sqlite3
import os
import time

router = APIRouter(tags=["health"])

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
DB_PATH = os.path.join(PROJECT_PATH, 'data', 'nifty100.db')
START_TIME = time.time()

@router.get("/health")
def health_check():
    db_row_counts = {}
    
    tables = [
        "profitandloss", "balancesheet", "cashflow", "companies",
        "analysis", "documents", "prosandcons", "sectors",
        "market_cap", "financial_ratios"
    ]
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    db_row_counts[table] = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    db_row_counts[table] = -1
    except Exception as e:
        return {"status": "error", "message": str(e)}

    uptime_seconds = int(time.time() - START_TIME)
    
    return {
        "status": "ok",
        "db_row_counts": db_row_counts,
        "uptime_seconds": uptime_seconds,
        "version": "1.0.0"
    }
