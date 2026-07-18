import streamlit as st
import sys
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

project_path = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(project_path)
os.chdir(project_path)

from src.dashboard.utils import db
from src.etl.loader import load_all_data

# Page config
st.set_page_config(
    page_title="Nifty 100 Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("🎯 Nifty 100 Analytics")
st.sidebar.markdown("---")

# Navigation
page = st.sidebar.radio(
    "📑 Select Screen",
    ["🏠 Home", "👤 Profile"]
)

# ════════════════════════════════════════════════════════════════════════════
# HOME SCREEN
# ════════════════════════════════════════════════════════════════════════════

if page == "🏠 Home":
    st.title("📊 Nifty 100 Financial Intelligence")
    st.markdown("Real-time analytics for 92 Nifty 100 companies")
    
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
            st.plotly_chart(fig, use_container_width=True, key="home_sector_pie")
        
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
                st.plotly_chart(fig, use_container_width=True, key="home_health_bar")
        
        # Summary table
        st.subheader("Top 10 Companies by ROE")
        top_roe = merged.nlargest(10, 'return_on_equity_pct')[
            ['company_id', 'broad_sector', 'return_on_equity_pct', 'return_on_capital_pct']
        ]
        st.dataframe(top_roe, use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════════════════════
# PROFILE SCREEN
# ════════════════════════════════════════════════════════════════════════════

elif page == "👤 Profile":
    st.title("👤 Company Profile")
    
    # Company search
    companies_df = db.get_companies()
    company_list = sorted(companies_df['id'].unique().tolist())
    
    ticker = st.selectbox(
        "Search Company",
        company_list,
        index=0
    )
    
    if ticker:
        # Get company info
        company_info = companies_df[companies_df['id'] == ticker]
        
        if len(company_info) > 0:
            info = company_info.iloc[0]
            
            # Company card
            st.subheader(f"📊 {ticker}")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Sector:** {info.get('sector', 'N/A')}")
            with col2:
                st.write(f"**Sub-sector:** {info.get('sub_sector', 'N/A')}")
            with col3:
                about_text = str(info.get('about', 'N/A'))[:50]
                st.write(f"**About:** {about_text}...")
            
            st.markdown("---")
            
            # Get latest year data
            latest_all = db.get_ratios(ticker=ticker)
            if len(latest_all) > 0:
                latest = latest_all.sort_values('year').iloc[-1]
                
                # KPI Tiles - SAFE CONVERSION
                st.subheader("Key Metrics (Latest Year)")
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                
                with col1:
                    try:
                        roe = float(latest.get('return_on_equity_pct', 0))
                    except:
                        roe = 0
                    st.metric("ROE", f"{roe:.1f}%")
                
                with col2:
                    try:
                        roce = float(latest.get('return_on_capital_pct', 0))
                    except:
                        roce = 0
                    st.metric("ROCE", f"{roce:.1f}%")
                
                with col3:
                    try:
                        npm = float(latest.get('net_profit_margin_pct', 0))
                    except:
                        npm = 0
                    st.metric("NPM", f"{npm:.1f}%")
                
                with col4:
                    try:
                        de = float(latest.get('debt_to_equity', 0))
                    except:
                        de = 0
                    st.metric("D/E", f"{de:.2f}")
                
                with col5:
                    try:
                        cagr = float(latest.get('sales_cagr_5yr', 0))
                    except:
                        cagr = 0
                    st.metric("Rev CAGR 5yr", f"{cagr:.1f}%")
                
                with col6:
                    try:
                        fcf = float(latest.get('free_cash_flow_cr', 0))
                    except:
                        fcf = 0
                    st.metric("FCF", f"₹{fcf:.0f}Cr")
                
                st.markdown("---")
                
                # 10-year trends
                company_data = db.get_ratios(ticker=ticker).sort_values('year')
                
                if len(company_data) > 1:
                    st.subheader("10-Year Return Metrics")
                    
                    # ROE + ROCE dual-axis (ONLY ONE CHART - NO DUPLICATES)
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=company_data['year'],
                        y=pd.to_numeric(company_data['return_on_equity_pct'], errors='coerce'),
                        name='ROE',
                        mode='lines+markers',
                        line=dict(color='#1f4e79', width=2)
                    ))
                    fig.add_trace(go.Scatter(
                        x=company_data['year'],
                        y=pd.to_numeric(company_data['return_on_capital_pct'], errors='coerce'),
                        name='ROCE',
                        mode='lines+markers',
                        line=dict(color='#ed7d31', width=2)
                    ))
                    fig.update_layout(
                        title="ROE vs ROCE Trend (10 Years)",
                        xaxis_title="Year",
                        yaxis_title="Return %",
                        height=400,
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig, use_container_width=True, key=f"profile_roe_roce_{ticker}")
            else:
                st.error(f"No financial data for {ticker}")
        else:
            st.error(f"Company {ticker} not found")

st.sidebar.markdown("---")
st.sidebar.caption("📊 Sprint 4 — Streamlit Dashboard")