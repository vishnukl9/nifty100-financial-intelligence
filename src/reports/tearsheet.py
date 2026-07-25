import sqlite3
import pandas as pd
import numpy as np
import os
import sys
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(PROJECT_PATH)

DB_PATH = os.path.join(PROJECT_PATH, 'data', 'nifty100.db')
OUTPUT_DIR = os.path.join(PROJECT_PATH, 'output')
TEARSHEETS_DIR = os.path.join(PROJECT_PATH, 'reports', 'tearsheets')

def create_charts(cid, group_pl, group_ratios, group_bs, group_cf):
    temp_dir = os.path.join(OUTPUT_DIR, 'temp_charts')
    os.makedirs(temp_dir, exist_ok=True)
    
    # 1. Revenue & Net Profit Bar
    plt.figure(figsize=(6, 3))
    years = group_pl['year'].apply(lambda x: str(x)[-2:] if isinstance(x, str) else x)
    x = np.arange(len(years))
    width = 0.35
    plt.bar(x - width/2, group_pl['sales'], width, label='Revenue', color='#1f77b4')
    plt.bar(x + width/2, group_pl['net_profit'], width, label='Net Profit', color='#ff7f0e')
    plt.xticks(x, years, rotation=45)
    plt.title("Revenue & Net Profit (10yr)")
    plt.legend()
    plt.tight_layout()
    chart1_path = os.path.join(temp_dir, f"{cid}_bar.png")
    plt.savefig(chart1_path)
    plt.close()

    # 2. ROE & ROCE Dual Axis Line
    plt.figure(figsize=(6, 3))
    fig, ax1 = plt.subplots(figsize=(6,3))
    
    r_years = group_ratios['year'].apply(lambda x: str(x)[-2:] if isinstance(x, str) else x)
    
    ax1.plot(r_years, group_ratios['return_on_equity_pct'], color='blue', marker='o', label='ROE')
    ax1.set_ylabel('ROE %', color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')
    
    # Check if ROCE exists in the DataFrame
    if 'return_on_capital_pct' in group_ratios.columns:
        roce = group_ratios['return_on_capital_pct']
    else:
        # Fallback to operating margin if ROCE is not found, just for visualization purposes
        roce = group_ratios.get('operating_profit_margin_pct', [0]*len(r_years))
        
    ax2 = ax1.twinx()
    ax2.plot(r_years, roce, color='green', marker='s', label='Margin/ROCE')
    ax2.set_ylabel('Margin/ROCE %', color='green')
    ax2.tick_params(axis='y', labelcolor='green')
    
    plt.title("Return Metrics Trend")
    fig.tight_layout()
    chart2_path = os.path.join(temp_dir, f"{cid}_line.png")
    plt.savefig(chart2_path)
    plt.close(fig)
    
    # 3. Balance Sheet Stacked Bar
    plt.figure(figsize=(6, 3))
    b_years = group_bs['year'].apply(lambda x: str(x)[-2:] if isinstance(x, str) else x)
    eq = group_bs['equity_capital'] + group_bs['reserves'].fillna(0)
    borr = group_bs['borrowings'].fillna(0)
    oth = group_bs['other_liabilities'].fillna(0)
    plt.bar(b_years, eq, label='Equity', color='#2ca02c')
    plt.bar(b_years, borr, bottom=eq, label='Borrowings', color='#d62728')
    plt.bar(b_years, oth, bottom=eq+borr, label='Other Liab', color='#7f7f7f')
    plt.xticks(rotation=45)
    plt.title("Balance Sheet Composition")
    plt.legend()
    plt.tight_layout()
    chart3_path = os.path.join(temp_dir, f"{cid}_bs.png")
    plt.savefig(chart3_path)
    plt.close()
    
    # 4. Cash Flow Waterfall (Latest Year)
    plt.figure(figsize=(6, 3))
    if not group_cf.empty:
        latest_cf = group_cf.iloc[-1]
        cfo = latest_cf.get('operating_activity', 0)
        cfi = latest_cf.get('investing_activity', 0)
        cff = latest_cf.get('financing_activity', 0)
        net_cf = cfo + cfi + cff
        
        cats = ['CFO', 'CFI', 'CFF', 'Net']
        vals = [cfo, cfi, cff, net_cf]
        colors_cf = ['g' if v > 0 else 'r' for v in vals]
        plt.bar(cats, vals, color=colors_cf)
        plt.title("Cash Flow (Latest Year)")
    plt.tight_layout()
    chart4_path = os.path.join(temp_dir, f"{cid}_cf.png")
    plt.savefig(chart4_path)
    plt.close()

    return chart1_path, chart2_path, chart3_path, chart4_path

def generate_tearsheets():
    os.makedirs(TEARSHEETS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with sqlite3.connect(DB_PATH) as conn:
        ratios_df = pd.read_sql("SELECT * FROM financial_ratios ORDER BY company_id, year", conn)
        pl_df = pd.read_sql("SELECT * FROM profitandloss ORDER BY company_id, year", conn)
        bs_df = pd.read_sql("SELECT * FROM balancesheet ORDER BY company_id, year", conn)
        cf_df = pd.read_sql("SELECT * FROM cashflow ORDER BY company_id, year", conn)
        companies_df = pd.read_sql("SELECT * FROM companies", conn)
        
    try:
        pros_cons = pd.read_csv(os.path.join(OUTPUT_DIR, 'pros_cons_generated.csv'))
    except:
        pros_cons = pd.DataFrame(columns=['company_id', 'type', 'text'])
        
    try:
        cf_intel = pd.read_excel(os.path.join(OUTPUT_DIR, 'cashflow_intelligence.xlsx'))
    except:
        cf_intel = pd.DataFrame(columns=['company_id', 'capital_allocation_label'])

    company_ids = companies_df['id'].unique()
    
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        'Header', parent=styles['Heading1'],
        textColor=colors.whitesmoke, backColor=colors.navy,
        alignment=1, spaceAfter=14, padding=10
    )
    pro_style = ParagraphStyle('Pro', parent=styles['Normal'], textColor=colors.green, spaceAfter=6)
    con_style = ParagraphStyle('Con', parent=styles['Normal'], textColor=colors.red, spaceAfter=6)
    
    skipped = []
    
    for cid in company_ids:
        group_pl = pl_df[pl_df['company_id'] == cid].tail(10)
        group_ratios = ratios_df[ratios_df['company_id'] == cid].tail(10)
        group_bs = bs_df[bs_df['company_id'] == cid].tail(10)
        group_cf = cf_df[cf_df['company_id'] == cid].tail(10)
        
        if len(group_pl) < 3 or len(group_ratios) < 1 or len(group_bs) < 1 or len(group_cf) < 1:
            skipped.append(cid)
            continue
            
        c_info = companies_df[companies_df['id'] == cid].iloc[0]
        c_pros = pros_cons[(pros_cons['company_id'] == cid) & (pros_cons['type'] == 'pro')]['text'].tolist()
        c_cons = pros_cons[(pros_cons['company_id'] == cid) & (pros_cons['type'] == 'con')]['text'].tolist()
        
        cf_intel_row = cf_intel[cf_intel['company_id'] == cid]
        cap_alloc = cf_intel_row['capital_allocation_label'].values[0] if not cf_intel_row.empty else "N/A"
        
        c1, c2, c3, c4 = create_charts(cid, group_pl, group_ratios, group_bs, group_cf)
        
        doc = SimpleDocTemplate(
            os.path.join(TEARSHEETS_DIR, f"{cid}_tearsheet.pdf"),
            pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30
        )
        
        elements = []
        
        # PAGE 1
        elements.append(Paragraph(f"<b>{c_info['company_name']} ({cid})</b>", header_style))
        
        # 6 KPI Tiles
        latest_ratio = group_ratios.iloc[-1]
        kpi_data = [
            ["ROE %", f"{latest_ratio.get('return_on_equity_pct', 0):.1f}%", "D/E Ratio", f"{latest_ratio.get('debt_to_equity', 0):.2f}"],
            ["Net Profit Mgn", f"{latest_ratio.get('net_profit_margin_pct', 0):.1f}%", "FCF (Cr)", f"{latest_ratio.get('free_cash_flow_cr', 0):.0f}"],
            ["Asset Turnover", f"{latest_ratio.get('asset_turnover', 0):.2f}", "Div Payout", f"{latest_ratio.get('dividend_payout_ratio_pct', 0):.1f}%"]
        ]
        
        kpi_table = Table(kpi_data, colWidths=[100, 80, 100, 80])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0,0), (-1,-1), 1, colors.white)
        ]))
        elements.append(kpi_table)
        elements.append(Spacer(1, 20))
        
        # Charts Page 1
        chart_table = Table([[Image(c1, width=220, height=150), Image(c2, width=220, height=150)]])
        elements.append(chart_table)
        elements.append(PageBreak())
        
        # PAGE 2
        elements.append(Paragraph(f"<b>{c_info['company_name']} - Financial Health & Profile</b>", header_style))
        chart_table2 = Table([[Image(c3, width=220, height=150), Image(c4, width=220, height=150)]])
        elements.append(chart_table2)
        elements.append(Spacer(1, 15))
        
        elements.append(Paragraph(f"<b>Capital Allocation Pattern:</b> {cap_alloc}", styles['Normal']))
        elements.append(Spacer(1, 15))
        
        elements.append(Paragraph("<b>Pros:</b>", styles['Heading3']))
        for pro in c_pros:
            elements.append(Paragraph(f"• {pro}", pro_style))
            
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("<b>Cons:</b>", styles['Heading3']))
        for con in c_cons:
            elements.append(Paragraph(f"• {con}", con_style))
            
        doc.build(elements)
        
    pd.DataFrame({'skipped_tickers': skipped}).to_csv(os.path.join(OUTPUT_DIR, 'skipped_tearsheets.csv'), index=False)
    print(f"Generated tearsheets. Skipped {len(skipped)} companies.")

if __name__ == "__main__":
    generate_tearsheets()
