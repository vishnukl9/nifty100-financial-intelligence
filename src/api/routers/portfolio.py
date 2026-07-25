from fastapi import APIRouter
import pandas as pd
import os

router = APIRouter(tags=["portfolio"])

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
OUTPUT_DIR = os.path.join(PROJECT_PATH, 'output')

@router.get("/portfolio/stats")
def get_portfolio_stats():
    stats_file = os.path.join(OUTPUT_DIR, 'portfolio_stats.csv')
    if os.path.exists(stats_file):
        df = pd.read_csv(stats_file)
        return df.to_dict(orient='records')
    return []
