from fastapi import APIRouter, HTTPException
import sqlite3
import os
import pandas as pd
from typing import List, Dict

router = APIRouter(tags=["peers"])

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
DB_PATH = os.path.join(PROJECT_PATH, 'data', 'nifty100.db')

def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

@router.get("/peers/{group_name}")
def get_peer_group(group_name: str):
    query = """
        SELECT c.id, c.company_name, p.group_name, p.benchmark_ticker,
               r.return_on_equity_pct as roe, r.debt_to_equity as de,
               r.operating_profit_margin_pct as opm, r.net_profit_margin_pct as npm,
               r.asset_turnover, r.interest_coverage, r.free_cash_flow_cr as fcf,
               r.capex_cr as capex
        FROM peer_groups p
        JOIN companies c ON p.company_id = c.id
        LEFT JOIN (
            SELECT * FROM financial_ratios
            WHERE year = (SELECT MAX(year) FROM financial_ratios f2 WHERE f2.company_id = financial_ratios.company_id)
        ) r ON c.id = r.company_id
        WHERE p.group_name = ?
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        cursor.execute(query, (group_name,))
        results = cursor.fetchall()
        
    if not results:
        raise HTTPException(status_code=404, detail="Peer group not found")
        
    # Calculate percentiles for the group
    df = pd.DataFrame(results)
    metrics = ['roe', 'de', 'opm', 'npm', 'asset_turnover', 'interest_coverage', 'fcf', 'capex']
    
    percentiles = {}
    for metric in metrics:
        if metric in df.columns and df[metric].notna().any():
            percentiles[f"{metric}_rank"] = df[metric].rank(pct=True).round(2).tolist()
        else:
            percentiles[f"{metric}_rank"] = [None] * len(df)
            
    for i in range(len(results)):
        for metric in metrics:
            results[i][f"{metric}_percentile"] = percentiles[f"{metric}_rank"][i]
            
    return results

@router.get("/companies/{ticker}/peers/compare")
def compare_company_peers(ticker: str):
    # 1. Find company's peer group
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        cursor.execute("SELECT group_name, benchmark_ticker FROM peer_groups WHERE company_id = ?", (ticker,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Peer group not found for company")
            
        group_name = row['group_name']
        benchmark = row['benchmark_ticker']
        
        # 2. Get data for company, benchmark, and group average
        query = """
            SELECT c.id, r.return_on_equity_pct as roe, r.debt_to_equity as de,
                   r.operating_profit_margin_pct as opm, r.net_profit_margin_pct as npm,
                   r.asset_turnover, r.interest_coverage, r.free_cash_flow_cr as fcf,
                   r.capex_cr as capex
            FROM peer_groups p
            JOIN companies c ON p.company_id = c.id
            LEFT JOIN (
                SELECT * FROM financial_ratios
                WHERE year = (SELECT MAX(year) FROM financial_ratios f2 WHERE f2.company_id = financial_ratios.company_id)
            ) r ON c.id = r.company_id
            WHERE p.group_name = ?
        """
        cursor.execute(query, (group_name,))
        group_data = cursor.fetchall()
        
    df = pd.DataFrame(group_data)
    
    company_data = df[df['id'] == ticker].iloc[0].to_dict() if len(df[df['id'] == ticker]) > 0 else {}
    benchmark_data = df[df['id'] == benchmark].iloc[0].to_dict() if len(df[df['id'] == benchmark]) > 0 else {}
    
    metrics = ['roe', 'de', 'opm', 'npm', 'asset_turnover', 'interest_coverage', 'fcf', 'capex']
    group_avg = df[metrics].mean().to_dict()
    
    return {
        "metrics": metrics,
        "company": company_data,
        "benchmark": benchmark_data,
        "group_average": group_avg
    }
