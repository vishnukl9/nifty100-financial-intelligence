import sqlite3
import pandas as pd
import numpy as np
import re
import os
import sys

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(PROJECT_PATH)

from src.analytics.cagr import compute_all_cagr

DB_PATH = os.path.join(PROJECT_PATH, 'data', 'nifty100.db')
OUTPUT_DIR = os.path.join(PROJECT_PATH, 'output')

def parse_analysis():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with sqlite3.connect(DB_PATH) as conn:
        analysis_df = pd.read_sql("SELECT * FROM analysis", conn)
        
    metrics = ['compounded_sales_growth', 'compounded_profit_growth', 'stock_price_cagr', 'roe']
    
    parsed_records = []
    failed_records = []
    
    # Matches strings like "10 Years: 21%" or "5 Years: 6%"
    pattern = re.compile(r'^(\d+)\s*Years?:?\s*([\d.-]+)%$', re.IGNORECASE)
    
    for _, row in analysis_df.iterrows():
        company_id = row['company_id']
        for metric in metrics:
            val = row[metric]
            if pd.isna(val) or not str(val).strip():
                continue
                
            val_str = str(val).strip()
            # Also remove trailing/leading spaces inside the string if any
            match = pattern.search(val_str)
            if match:
                period_years = int(match.group(1))
                value_pct = float(match.group(2))
                parsed_records.append({
                    'company_id': company_id,
                    'metric_type': metric,
                    'period_years': period_years,
                    'value_pct': value_pct
                })
            else:
                failed_records.append({
                    'company_id': company_id,
                    'metric_type': metric,
                    'raw_value': val_str
                })
                
    parsed_df = pd.DataFrame(parsed_records)
    failures_df = pd.DataFrame(failed_records)
    
    parsed_csv_path = os.path.join(OUTPUT_DIR, 'analysis_parsed.csv')
    failures_csv_path = os.path.join(OUTPUT_DIR, 'parse_failures.csv')
    
    if not parsed_df.empty:
        parsed_df.to_csv(parsed_csv_path, index=False)
    if not failures_df.empty:
        failures_df.to_csv(failures_csv_path, index=False)
        
    print(f"Parsed records saved to {parsed_csv_path}")
    print(f"Failed records saved to {failures_csv_path}")
    
    # Cross-validation
    print("Cross-validating against computed CAGR...")
    cagr_df = compute_all_cagr()
    
    divergence_records = []
    
    if not parsed_df.empty and cagr_df is not None:
        for _, row in parsed_df.iterrows():
            company_id = row['company_id']
            metric_type = row['metric_type']
            period_years = row['period_years']
            parsed_val = row['value_pct']
            
            cagr_col = None
            if metric_type == 'compounded_sales_growth':
                cagr_col = f'sales_cagr_{period_years}yr'
            elif metric_type == 'compounded_profit_growth':
                cagr_col = f'net_profit_cagr_{period_years}yr'
                
            if cagr_col and cagr_col in cagr_df.columns:
                comp_data = cagr_df[cagr_df['company_id'] == company_id]
                if not comp_data.empty:
                    computed_val = comp_data[cagr_col].values[0]
                    if pd.notna(computed_val):
                        diff = abs(parsed_val - computed_val)
                        if diff > 5.0:
                            divergence_records.append({
                                'company_id': company_id,
                                'metric': metric_type,
                                'period': period_years,
                                'parsed_cagr': parsed_val,
                                'computed_cagr': computed_val,
                                'divergence': round(diff, 2)
                            })
                            
    if divergence_records:
        div_df = pd.DataFrame(divergence_records)
        div_path = os.path.join(OUTPUT_DIR, 'cagr_divergence.csv')
        div_df.to_csv(div_path, index=False)
        print(f"Found {len(divergence_records)} divergences > 5%. Saved to {div_path}")
    else:
        print("No significant divergence found between parsed and computed CAGRs.")

if __name__ == "__main__":
    parse_analysis()
