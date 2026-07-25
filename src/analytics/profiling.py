import sqlite3
import pandas as pd
import numpy as np
import os
import sys
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.stats import zscore

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(PROJECT_PATH)

DB_PATH = os.path.join(PROJECT_PATH, 'data', 'nifty100.db')
REPORTS_DIR = os.path.join(PROJECT_PATH, 'reports')
OUTPUT_DIR = os.path.join(PROJECT_PATH, 'output')

def compute_cagr(start_value, end_value, n_years):
    if pd.isna(start_value) or pd.isna(end_value):
        return np.nan
    if n_years < 1 or start_value == 0:
        return np.nan
    if start_value < 0 or end_value < 0:
        return np.nan
    try:
        return ((end_value / start_value) ** (1 / n_years) - 1) * 100
    except:
        return np.nan

def profile_clusters():
    # 1. Load Data
    with sqlite3.connect(DB_PATH) as conn:
        ratios = pd.read_sql("SELECT * FROM financial_ratios ORDER BY company_id, year", conn)
        companies = pd.read_sql("SELECT * FROM companies", conn)
        sectors = pd.read_sql("SELECT * FROM sectors", conn)

    latest = ratios.sort_values('year').groupby('company_id').tail(1).copy()
    
    # Re-compute FCF CAGR
    fcf_cagr_list = []
    for cid, group in ratios.groupby('company_id'):
        group = group.sort_values('year')
        if len(group) >= 6:
            end_val = group.iloc[-1]['free_cash_flow_cr']
            start_val = group.iloc[-6]['free_cash_flow_cr']
            val = compute_cagr(start_val, end_val, 5)
        else:
            val = np.nan
        fcf_cagr_list.append({'company_id': cid, 'fcf_cagr_5yr': val})
    fcf_df = pd.DataFrame(fcf_cagr_list)
    
    from src.analytics.cagr import compute_all_cagr
    cagr_df = compute_all_cagr()
    
    df = latest[['company_id', 'return_on_equity_pct', 'debt_to_equity', 'operating_profit_margin_pct', 'net_profit_margin_pct', 'asset_turnover', 'interest_coverage', 'free_cash_flow_cr', 'capex_cr']]
    df = df.merge(fcf_df, on='company_id', how='left')
    df = df.merge(cagr_df[['company_id', 'sales_cagr_5yr', 'net_profit_cagr_5yr']], on='company_id', how='left')
    df.rename(columns={'sales_cagr_5yr': 'revenue_cagr_5yr', 'net_profit_cagr_5yr': 'pat_cagr_5yr'}, inplace=True)
    df = df.merge(sectors[['company_id', 'broad_sector']], on='company_id', how='left')
    
    # Load cluster labels
    cluster_labels_path = os.path.join(OUTPUT_DIR, 'cluster_labels.csv')
    if not os.path.exists(cluster_labels_path):
        print("Cluster labels not found. Run clustering.py first.")
        return
        
    labels = pd.read_csv(cluster_labels_path)
    df = df.merge(labels[['company_id', 'cluster_id']], on='company_id')
    
    features = ['return_on_equity_pct', 'debt_to_equity', 'revenue_cagr_5yr', 'fcf_cagr_5yr', 'operating_profit_margin_pct']
    
    # Assign Names
    profile = df.groupby('cluster_id')[features].median()
    cluster_names = {}
    for cid, row in profile.iterrows():
        if row['debt_to_equity'] > 2.0 or row['return_on_equity_pct'] < 5:
            cluster_names[cid] = "Distressed or Turnaround"
        elif row['revenue_cagr_5yr'] > 15 and row['fcf_cagr_5yr'] > 15:
            cluster_names[cid] = "Emerging Growth"
        elif row['return_on_equity_pct'] > 15 and row['operating_profit_margin_pct'] > 15:
            cluster_names[cid] = "High-Quality Compounders"
        elif row['debt_to_equity'] < 0.5:
            cluster_names[cid] = "Defensive Dividend Payers"
        else:
            cluster_names[cid] = "Value Cyclicals"
            
    # Update cluster labels
    labels['cluster_name'] = labels['cluster_id'].map(cluster_names)
    labels.to_csv(cluster_labels_path, index=False)
    
    # 2. Correlation Heatmap
    kpi_cols = ['return_on_equity_pct', 'debt_to_equity', 'operating_profit_margin_pct', 'net_profit_margin_pct', 'asset_turnover', 'interest_coverage', 'revenue_cagr_5yr', 'pat_cagr_5yr', 'free_cash_flow_cr', 'capex_cr']
    corr_df = df[kpi_cols].corr()
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(corr_df, annot=True, cmap='coolwarm', fmt=".2f")
    plt.title("KPI Correlation Heatmap")
    plt.tight_layout()
    plt.savefig(os.path.join(REPORTS_DIR, 'correlation_heatmap.png'))
    plt.close()
    
    # 3. Outlier Detection
    outliers = []
    for sector in df['broad_sector'].unique():
        sec_df = df[df['broad_sector'] == sector]
        for col in kpi_cols:
            if sec_df[col].dropna().nunique() > 1:
                z = np.abs(zscore(sec_df[col].dropna().values))
                outlier_indices = sec_df[col].dropna().index[z > 3]
                for idx in outlier_indices:
                    outliers.append({
                        'company_id': sec_df.loc[idx, 'company_id'],
                        'broad_sector': sector,
                        'metric': col,
                        'value': sec_df.loc[idx, col],
                        'z_score': z[sec_df[col].dropna().index == idx][0]
                    })
    
    outliers_df = pd.DataFrame(outliers)
    outliers_df.to_csv(os.path.join(OUTPUT_DIR, 'outlier_report.csv'), index=False)
    
    # 4. Portfolio Stats
    stats_list = []
    for col in kpi_cols:
        series = df[col].dropna()
        if len(series) > 0:
            stats_list.append({
                'KPI': col,
                'P10': series.quantile(0.10),
                'P25': series.quantile(0.25),
                'P50': series.quantile(0.50),
                'P75': series.quantile(0.75),
                'P90': series.quantile(0.90),
                'Mean': series.mean(),
                'Std': series.std()
            })
            
    stats_df = pd.DataFrame(stats_list)
    stats_df.to_csv(os.path.join(OUTPUT_DIR, 'portfolio_stats.csv'), index=False)
    
    print("Profiling complete. Updated cluster_labels.csv, saved heatmap, outliers, and stats.")

if __name__ == "__main__":
    profile_clusters()
