import sqlite3
import pandas as pd
import numpy as np
import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(PROJECT_PATH)

DB_PATH = os.path.join(PROJECT_PATH, 'data', 'nifty100.db')
PORTFOLIO_DIR = os.path.join(PROJECT_PATH, 'reports', 'portfolio')

def generate_portfolio_report():
    os.makedirs(PORTFOLIO_DIR, exist_ok=True)
    
    with sqlite3.connect(DB_PATH) as conn:
        ratios_df = pd.read_sql("SELECT * FROM financial_ratios ORDER BY company_id, year", conn)
        companies_df = pd.read_sql("SELECT * FROM companies ORDER BY id", conn)
        sectors_df = pd.read_sql("SELECT * FROM sectors", conn)

    doc = SimpleDocTemplate(
        os.path.join(PORTFOLIO_DIR, "portfolio_summary.pdf"),
        pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle('Header', parent=styles['Heading1'], textColor=colors.whitesmoke, backColor=colors.navy, alignment=1, spaceAfter=14, padding=10)
    
    elements = []
    
    for _, c_row in companies_df.iterrows():
        cid = c_row['id']
        c_name = c_row['company_name']
        
        c_sector = sectors_df[sectors_df['company_id'] == cid]['broad_sector'].values
        sector = c_sector[0] if len(c_sector) > 0 else 'Unknown'
        
        c_ratios = ratios_df[ratios_df['company_id'] == cid]
        if len(c_ratios) < 2:
            continue
            
        latest = c_ratios.iloc[-1]
        prev = c_ratios.iloc[-2]
        
        elements.append(Paragraph(f"<b>{c_name} ({cid})</b>", header_style))
        elements.append(Paragraph(f"<b>Sector:</b> {sector}", styles['Heading3']))
        elements.append(Spacer(1, 20))
        
        # 6 KPIs
        def get_trend(metric):
            curr = latest.get(metric)
            prv = prev.get(metric)
            if pd.isna(curr) or pd.isna(prv) or prv == 0:
                return ""
            change = (curr - prv) / abs(prv)
            if change > 0.02:
                return "↑"
            elif change < -0.02:
                return "↓"
            else:
                return "→"
                
        metrics = [
            ('Return on Equity', 'return_on_equity_pct', True),
            ('Return on Capital', 'return_on_capital_pct', True), # Fallback to OPM if not present
            ('Net Profit Margin', 'net_profit_margin_pct', True),
            ('Debt to Equity', 'debt_to_equity', False), # For D/E, lower is better, so maybe logic changes, but we just show arrow
            ('Free Cash Flow (Cr)', 'free_cash_flow_cr', True),
            ('Asset Turnover', 'asset_turnover', True)
        ]
        
        table_data = [["Metric", "Latest Value", "Trend"]]
        for name, col, _ in metrics:
            val = latest.get(col, np.nan)
            
            # fallback for ROCE if not present
            if col == 'return_on_capital_pct' and pd.isna(val):
                col = 'operating_profit_margin_pct'
                val = latest.get(col, np.nan)
                
            val_str = f"{val:.2f}" if pd.notna(val) else "N/A"
            trend = get_trend(col)
            table_data.append([name, val_str, trend])
            
        t = Table(table_data, colWidths=[200, 150, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        
        elements.append(t)
        elements.append(PageBreak())
        
    doc.build(elements)
    print("Portfolio summary generated.")

if __name__ == "__main__":
    generate_portfolio_report()
