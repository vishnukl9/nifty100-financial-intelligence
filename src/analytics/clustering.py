import sqlite3
import pandas as pd
import numpy as np
import os
import sys
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns

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

def generate_clusters():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        ratios = pd.read_sql("SELECT * FROM financial_ratios ORDER BY company_id, year", conn)
        companies = pd.read_sql("SELECT * FROM companies", conn)
        sectors = pd.read_sql("SELECT * FROM sectors", conn)

    # We need latest year data for roe, de, opm
    latest = ratios.sort_values('year').groupby('company_id').tail(1).copy()
    
    # Compute 5yr FCF CAGR
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
    
    # Import revenue_cagr_5yr from cagr.py
    from src.analytics.cagr import compute_all_cagr
    cagr_df = compute_all_cagr()
    
    # Merge datasets
    df = latest[['company_id', 'return_on_equity_pct', 'debt_to_equity', 'operating_profit_margin_pct']]
    df = df.merge(fcf_df, on='company_id', how='left')
    df = df.merge(cagr_df[['company_id', 'sales_cagr_5yr']], on='company_id', how='left')
    df.rename(columns={'sales_cagr_5yr': 'revenue_cagr_5yr'}, inplace=True)
    
    # Merge sector info for imputation
    df = df.merge(sectors[['company_id', 'broad_sector']], on='company_id', how='left')
    
    features = ['return_on_equity_pct', 'debt_to_equity', 'revenue_cagr_5yr', 'fcf_cagr_5yr', 'operating_profit_margin_pct']
    
    # Impute missing values with sector median
    for feature in features:
        df[feature] = df.groupby('broad_sector')[feature].transform(lambda x: x.fillna(x.median()))
        # If sector median is also NaN, fill with overall median
        df[feature] = df[feature].fillna(df[feature].median())
        
    # Scaling
    X = df[features].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Elbow Plot
    inertias = []
    k_range = range(2, 11)
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init='auto')
        km.fit(X_scaled)
        inertias.append(km.inertia_)
        
    plt.figure(figsize=(8, 5))
    plt.plot(k_range, inertias, marker='o', linestyle='--')
    plt.title('Elbow Plot for KMeans Clustering')
    plt.xlabel('Number of Clusters (k)')
    plt.ylabel('Inertia')
    plt.grid(True)
    plt.savefig(os.path.join(REPORTS_DIR, 'elbow_plot.png'))
    plt.close()
    
    # Fit final KMeans with k=5
    kmeans = KMeans(n_clusters=5, random_state=42, n_init='auto')
    cluster_ids = kmeans.fit_predict(X_scaled)
    df['cluster_id'] = cluster_ids
    
    # Calculate distance from centroid
    centroids = kmeans.cluster_centers_
    distances = [np.linalg.norm(X_scaled[i] - centroids[cluster_ids[i]]) for i in range(len(X_scaled))]
    df['distance_from_centroid'] = distances
    
    # Initial placeholder for cluster_name
    df['cluster_name'] = df['cluster_id'].apply(lambda x: f"Cluster {x}")
    
    out_df = df[['company_id', 'cluster_id', 'cluster_name', 'distance_from_centroid']]
    out_df.to_csv(os.path.join(OUTPUT_DIR, 'cluster_labels.csv'), index=False)
    print("Clustering complete. Outputs generated in reports/ and output/ directories.")

if __name__ == "__main__":
    generate_clusters()
