import streamlit as st
import sys
import os

project_path = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(project_path)
os.chdir(project_path)

# Page config
st.set_page_config(
    page_title="Nifty 100 Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("🎯 Nifty 100 Analytics")
st.sidebar.markdown("---")

# Home page content directly in app.py
st.title("📊 Nifty 100 Financial Intelligence")
st.markdown("Real-time analytics for 92 Nifty 100 companies")

from src.dashboard.utils import db
import plotly.graph_objects as go
import plotly.express as px

# Year selector
col1, col2 = st.columns([3, 1])
with col2:
    year = st.selectbox(
        "Select Year",
        ["2024-03", "2023-03", "2022-03"],
        index=0
    )

# Load data
ratios = db.get_ratios(year=year)
sectors = db.get_sectors()

if len(ratios) == 0:
    st.error(f"No data for year {year}")
else:
    # Load market cap for P/E
    from src.etl.loader import load_all_data
    data = load_all_data()
    market_cap = data['market_cap']
    latest_mc = market_cap[market_cap['year'] == 2024][['company_id', 'pe_ratio']]
    
    # Merge with sectors and market cap
    merged = ratios.merge(sectors[['company_id', 'broad_sector']], on='company_id', how='left')
    merged = merged.merge(latest_mc, on='company_id', how='left')
    
    # ── KPI Tiles ──────────────────────────────────────────────────
    st.subheader("Key Metrics")
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        avg_roe = merged['return_on_equity_pct'].median()
        st.metric("Median ROE", f"{avg_roe:.1f}%")
    
    with col2:
        total_companies = merged['company_id'].nunique()
        st.metric("Companies", total_companies)
    
    with col3:
        median_de = merged['debt_to_equity'].median()
        st.metric("Median D/E", f"{median_de:.2f}")
    
    with col4:
        median_rev_cagr = merged['sales_cagr_5yr'].median()
        st.metric("Revenue CAGR 5yr", f"{median_rev_cagr:.1f}%")
    
    with col5:
        debt_free = (merged['debt_to_equity'] == 0).sum()
        st.metric("Debt-Free", debt_free)
    
    with col6:
        median_pe = merged['pe_ratio'].median()
        st.metric("Median P/E", f"{median_pe:.1f}x")
    
    st.markdown("---")
    
    # ── Charts ────────────────────────────────────────────────────
    st.subheader("Analysis")
    
    col1, col2 = st.columns(2)
    
    # Sector breakdown
    with col1:
        sector_counts = merged['broad_sector'].value_counts()
        fig = go.Figure(data=[
            go.Pie(labels=sector_counts.index, values=sector_counts.values,
                   hole=0.3, marker=dict(colors=px.colors.qualitative.Set3))
        ])
        fig.update_layout(title="Companies by Sector", height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Top 5 by health score
    with col2:
        if 'health_score' in merged.columns:
            top5 = merged.nlargest(5, 'health_score')[['company_id', 'health_score']]
            fig = go.Figure(data=[
                go.Bar(x=top5['company_id'], y=top5['health_score'],
                       marker=dict(color='#1f4e79'))
            ])
            fig.update_layout(
                title="Top 5 by Health Score",
                xaxis_title="Company",
                yaxis_title="Score",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Summary table
    st.subheader("Top 10 Companies by ROE")
    top_roe = merged.nlargest(10, 'return_on_equity_pct')[
        ['company_id', 'broad_sector', 'return_on_equity_pct', 'return_on_capital_pct']
    ]
    st.dataframe(top_roe, use_container_width=True, hide_index=True)

st.sidebar.markdown("---")
st.sidebar.caption("📊 Sprint 4 — Streamlit Dashboard")