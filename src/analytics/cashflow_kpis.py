import sqlite3
import pandas as pd
import numpy as np
import os
import sys

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(PROJECT_PATH)

from src.analytics.cagr import compute_cagr

DB_PATH = os.path.join(PROJECT_PATH, 'data', 'nifty100.db')
OUTPUT_DIR = os.path.join(PROJECT_PATH, 'output')

def get_capital_allocation_pattern(cfo, cfi, cff):
    cfo_sign = '+' if pd.notna(cfo) and cfo >= 0 else '-'
    cfi_sign = '+' if pd.notna(cfi) and cfi >= 0 else '-'
    cff_sign = '+' if pd.notna(cff) and cff >= 0 else '-'
    pattern  = f"({cfo_sign},{cfi_sign},{cff_sign})"

    pattern_map = {
        '(+,-,-)': 'Reinvestor',
        '(+,-,+)': 'Aggressive Expander',
        '(+,+,-)': 'Asset Seller',
        '(+,+,+)': 'Cash Accumulator',
        '(-,-,+)': 'Distress Signal',
        '(-,+,+)': 'Distress Signal',
        '(-,-,-)': 'Contraction',
        '(-,+,-)': 'Restructuring',
    }
    return pattern, pattern_map.get(pattern, 'Other')

def compute_fcf(df):
    df['free_cash_flow_cr'] = df['operating_activity'] + df['investing_activity']
    return df

def compute_cfo_quality(df):
    ratios = []
    for _, row in df.iterrows():
        if pd.notna(row.get('net_profit')) and row['net_profit'] != 0:
            ratios.append(row['operating_activity'] / row['net_profit'])
    
    score = np.mean(ratios) if ratios else np.nan
    label = 'N/A'
    if pd.notna(score):
        if score > 1.0:
            label = 'High Quality'
        elif score >= 0.5:
            label = 'Moderate'
        else:
            label = 'Accrual Risk'
    df['cfo_quality_score'] = score
    df['cfo_quality_label'] = label
    return df

def compute_capex_intensity(df):
    intensity = np.nan
    label = 'N/A'
    latest = df.iloc[-1]
    if pd.notna(latest.get('sales')) and latest['sales'] > 0:
        capex = abs(latest['investing_activity']) if pd.notna(latest.get('investing_activity')) else 0
        intensity = (capex / latest['sales']) * 100
        if intensity < 3:
            label = 'Asset Light'
        elif intensity < 8:
            label = 'Moderate'
        else:
            label = 'Capital Intensive'
    df['capex_intensity_pct'] = intensity
    df['capex_label'] = label
    return df

def generate_cashflow_intelligence():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with sqlite3.connect(DB_PATH) as conn:
        cf_df = pd.read_sql("SELECT * FROM cashflow ORDER BY company_id, year", conn)
        pl_df = pd.read_sql("SELECT * FROM profitandloss ORDER BY company_id, year", conn)
        bs_df = pd.read_sql("SELECT * FROM balancesheet ORDER BY company_id, year", conn)
        sectors_df = pd.read_sql("SELECT * FROM sectors", conn)
        
    merged = pd.merge(cf_df, pl_df, on=['company_id', 'year'], how='inner')
    merged = pd.merge(merged, bs_df, on=['company_id', 'year'], how='inner')
    
    # Calculate FCF
    merged['fcf'] = merged['operating_activity'] + merged['investing_activity']
    
    cf_intel_records = []
    distress_alerts = []
    allocation_records = []
    pattern_changes = []
    
    company_ids = merged['company_id'].unique()
    
    for cid in company_ids:
        group = merged[merged['company_id'] == cid].sort_values('year').reset_index(drop=True)
        if group.empty:
            continue
            
        latest = group.iloc[-1]
        c_sector = sectors_df[sectors_df['company_id'] == cid]['broad_sector'].values
        sector = c_sector[0] if len(c_sector) > 0 else 'Unknown'
        
        # CFO Quality Score (5-year average of CFO/PAT)
        last_5 = group.tail(5)
        ratios = []
        for _, row in last_5.iterrows():
            if pd.notna(row['net_profit']) and row['net_profit'] != 0:
                ratios.append(row['operating_activity'] / row['net_profit'])
        
        cfo_quality_score = np.nan
        cfo_quality_label = 'N/A'
        if ratios:
            cfo_quality_score = np.mean(ratios)
            if cfo_quality_score > 1.0:
                cfo_quality_label = 'High Quality'
            elif cfo_quality_score > 0.5:
                cfo_quality_label = 'Moderate'
            else:
                cfo_quality_label = 'Accrual Risk'
                
        # CapEx Intensity
        capex_intensity_pct = np.nan
        capex_label = 'N/A'
        if pd.notna(latest['sales']) and latest['sales'] > 0:
            capex = abs(latest['investing_activity']) if pd.notna(latest['investing_activity']) else 0
            capex_intensity_pct = (capex / latest['sales']) * 100
            if capex_intensity_pct < 3:
                capex_label = 'Asset Light'
            elif capex_intensity_pct < 8:
                capex_label = 'Moderate'
            else:
                capex_label = 'Capital Intensive'
                
        # Distress Signal & Deleveraging
        distress_flag = False
        deleveraging_flag = False
        
        cfo = latest.get('operating_activity', 0)
        cff = latest.get('financing_activity', 0)
        
        if cfo < 0 and cff > 0:
            distress_flag = True
            distress_alerts.append({
                'company_id': cid,
                'cfo': cfo,
                'cff': cff,
                'net_profit': latest.get('net_profit')
            })
            
        if len(group) >= 2:
            prev = group.iloc[-2]
            if cff < 0 and latest.get('borrowings', 0) < prev.get('borrowings', 0):
                deleveraging_flag = True
                
        # FCF CAGR 5yr
        fcf_cagr_5yr = np.nan
        if len(group) >= 5:
            start_fcf = group.iloc[-5]['fcf']
            end_fcf = latest['fcf']
            val, _ = compute_cagr(start_fcf, end_fcf, 5)
            if val is not None:
                fcf_cagr_5yr = val
                
        # FCF Conversion % = FCF / EBITDA (operating_profit)
        fcf_conversion_pct = np.nan
        ebitda = latest.get('operating_profit')
        if pd.notna(ebitda) and ebitda > 0 and pd.notna(latest['fcf']):
            fcf_conversion_pct = (latest['fcf'] / ebitda) * 100
            
        # Capital Allocation Patterns
        prev_label = None
        for i, row in group.iterrows():
            pat, lab = get_capital_allocation_pattern(row['operating_activity'], row['investing_activity'], row['financing_activity'])
            allocation_records.append({
                'company_id': cid,
                'year': row['year'],
                'CFO_sign': '+' if row['operating_activity'] >= 0 else '-',
                'CFI_sign': '+' if row['investing_activity'] >= 0 else '-',
                'CFF_sign': '+' if row['financing_activity'] >= 0 else '-',
                'pattern_label': lab
            })
            if i == len(group) - 1:
                latest_cf_label = lab
                
            if prev_label and prev_label != lab and i == len(group) - 1:
                pattern_changes.append({
                    'company_id': cid,
                    'year': row['year'],
                    'previous_pattern': prev_label,
                    'new_pattern': lab
                })
            prev_label = lab
            
        cf_intel_records.append({
            'company_id': cid,
            'sector': sector,
            'cfo_quality_score': round(cfo_quality_score, 2) if pd.notna(cfo_quality_score) else np.nan,
            'cfo_quality_label': cfo_quality_label,
            'capex_intensity_pct': round(capex_intensity_pct, 2) if pd.notna(capex_intensity_pct) else np.nan,
            'capex_label': capex_label,
            'fcf_cagr_5yr': round(fcf_cagr_5yr, 2) if pd.notna(fcf_cagr_5yr) else np.nan,
            'fcf_conversion_pct': round(fcf_conversion_pct, 2) if pd.notna(fcf_conversion_pct) else np.nan,
            'distress_flag': distress_flag,
            'deleveraging_flag': deleveraging_flag,
            'capital_allocation_label': latest_cf_label
        })

    # Save Cashflow Intelligence
    intel_df = pd.DataFrame(cf_intel_records)
    intel_df.to_excel(os.path.join(OUTPUT_DIR, 'cashflow_intelligence.xlsx'), index=False)
    
    # Save Distress Alerts
    if distress_alerts:
        distress_df = pd.DataFrame(distress_alerts)
        distress_df.to_csv(os.path.join(OUTPUT_DIR, 'distress_alerts.csv'), index=False)
    else:
        pd.DataFrame(columns=['company_id', 'cfo', 'cff', 'net_profit']).to_csv(os.path.join(OUTPUT_DIR, 'distress_alerts.csv'), index=False)
        
    # Save Capital Allocation full
    alloc_df = pd.DataFrame(allocation_records)
    alloc_df.to_csv(os.path.join(OUTPUT_DIR, 'capital_allocation.csv'), index=False)
    
    # Save Pattern Changes
    if pattern_changes:
        changes_df = pd.DataFrame(pattern_changes)
        changes_df.to_csv(os.path.join(OUTPUT_DIR, 'pattern_changes.csv'), index=False)
    else:
        pd.DataFrame(columns=['company_id', 'year', 'previous_pattern', 'new_pattern']).to_csv(os.path.join(OUTPUT_DIR, 'pattern_changes.csv'), index=False)

    # Print distribution summary for latest year
    latest_alloc = alloc_df.drop_duplicates('company_id', keep='last')
    dist = latest_alloc['pattern_label'].value_counts()
    print("Capital Allocation Distribution (Latest Year):")
    print(dist)

if __name__ == "__main__":
    generate_cashflow_intelligence()
