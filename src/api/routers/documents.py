from fastapi import APIRouter
import sqlite3
import os

router = APIRouter(tags=["documents"])

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
DB_PATH = os.path.join(PROJECT_PATH, 'data', 'nifty100.db')

def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

@router.get("/companies/{ticker}/documents")
def get_company_documents(ticker: str):
    query = """
        SELECT year, document_type, document_url
        FROM documents
        WHERE company_id = ?
        ORDER BY year DESC
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        cursor.execute(query, (ticker,))
        results = cursor.fetchall()
        
    for res in results:
        res['is_url_valid'] = res['document_url'].startswith('http') if res['document_url'] else False
        
    return results
