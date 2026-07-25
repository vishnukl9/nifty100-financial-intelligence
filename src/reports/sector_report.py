import sqlite3
import pandas as pd
import numpy as np
import os
import sys
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(PROJECT_PATH)

DB_PATH = os.path.join(PROJECT_PATH, 'data', 'nifty100.db')
SECTOR_DIR = os.path.join(PROJECT_PATH, 'reports', 'sector')

def generate_sector_reports():
    os.makedirs(SECTOR_DIR, exist_ok=True)
    
    with sqlite3.connect(DB_PATH) as conn:
        query = """
            SELECT c.company_name, c.id as ticker, s.broad_sector, 
                   r.return_on_equity_pct as roe, 
                   r.debt_to_equity as de, 
                   r.net_profit_margin_pct as npm,
                   r.operating_profit_margin_pct as opm,
                   r.asset_turnover as asset_turnover,
                   r.free_cash_flow_cr as fcf,
                   r.year
            FROM companies c
            JOIN sectors s ON c.id = s.company_id
            JOIN financial_ratios r ON c.id = r.company_id
        """
        df = pd.read_sql(query, conn)
        
    from src.analytics.cagr import compute_all_cagr
    cagr_df = compute_all_cagr()
    
    if cagr_df is not None:
        df = pd.merge(df, cagr_df[['company_id', 'net_profit_cagr_5yr', 'sales_cagr_5yr']], 
                      left_on='ticker', right_on='company_id', how='left')
    else:
        df['net_profit_cagr_5yr'] = np.nan
        df['sales_cagr_5yr'] = np.nan

    # Get latest year for each company
    latest_df = df.sort_values('year').groupby('ticker').tail(1)
    sectors = latest_df['broad_sector'].unique()
    
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle('Header', parent=styles['Heading1'], textColor=colors.whitesmoke, backColor=colors.navy, alignment=1, spaceAfter=14, padding=10)
    
    for sector in sectors:
        sector_df = latest_df[latest_df['broad_sector'] == sector]
        
        doc = SimpleDocTemplate(os.path.join(SECTOR_DIR, f"{sector.replace(' ', '_').replace('/', '_')}_report.pdf"), pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=30)
        elements = []
        
        elements.append(Paragraph(f"<b>{sector} - Sector Report</b>", header_style))
        elements.append(Spacer(1, 10))
        
        medians = sector_df[['roe', 'de', 'npm', 'opm', 'asset_turnover', 'fcf', 'net_profit_cagr_5yr', 'sales_cagr_5yr']].median()
        
        median_data = [
            ["Median ROE", f"{medians.get('roe', 0):.1f}%", "Median D/E", f"{medians.get('de', 0):.2f}"],
            ["Median NPM", f"{medians.get('npm', 0):.1f}%", "Median OPM", f"{medians.get('opm', 0):.1f}%"],
            ["Median FCF (Cr)", f"{medians.get('fcf', 0):.0f}", "Median PAT CAGR 5yr", f"{medians.get('net_profit_cagr_5yr', 0):.1f}%"]
        ]
        
        med_table = Table(median_data, colWidths=[120, 80, 120, 80])
        med_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 1, colors.white),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8)
        ]))
        elements.append(med_table)
        elements.append(Spacer(1, 20))
        
        # Companies List Table
        headers = ['Company', 'Ticker', 'ROE %', 'D/E', 'NPM %', 'OPM %', 'Asset T.O.', 'FCF', 'PAT CAGR', 'Sales CAGR']
        table_data = [headers]
        
        for _, row in sector_df.iterrows():
            table_data.append([
                Paragraph(row['company_name'], styles['Normal']),
                row['ticker'],
                f"{row.get('roe', 0):.1f}%" if pd.notna(row.get('roe')) else "N/A",
                f"{row.get('de', 0):.2f}" if pd.notna(row.get('de')) else "N/A",
                f"{row.get('npm', 0):.1f}%" if pd.notna(row.get('npm')) else "N/A",
                f"{row.get('opm', 0):.1f}%" if pd.notna(row.get('opm')) else "N/A",
                f"{row.get('asset_turnover', 0):.2f}" if pd.notna(row.get('asset_turnover')) else "N/A",
                f"{row.get('fcf', 0):.0f}" if pd.notna(row.get('fcf')) else "N/A",
                f"{row.get('net_profit_cagr_5yr', 0):.1f}%" if pd.notna(row.get('net_profit_cagr_5yr')) else "N/A",
                f"{row.get('sales_cagr_5yr', 0):.1f}%" if pd.notna(row.get('sales_cagr_5yr')) else "N/A"
            ])
            
        t = Table(table_data, colWidths=[180, 60, 60, 50, 60, 60, 70, 70, 70, 70])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'), # Left align company names
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        elements.append(t)
        doc.build(elements)
        
    print(f"Generated sector reports for {len(sectors)} sectors.")

if __name__ == "__main__":
    generate_sector_reports()
