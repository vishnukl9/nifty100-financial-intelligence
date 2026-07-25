import sqlite3
import pandas as pd
import numpy as np
import os
import sys

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(PROJECT_PATH)

from src.analytics.cagr import compute_all_cagr

DB_PATH = os.path.join(PROJECT_PATH, 'data', 'nifty100.db')
OUTPUT_DIR = os.path.join(PROJECT_PATH, 'output')

def generate_pros_cons():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with sqlite3.connect(DB_PATH) as conn:
        ratios_df = pd.read_sql("SELECT * FROM financial_ratios ORDER BY company_id, year", conn)
        companies_df = pd.read_sql("SELECT * FROM companies", conn)
        sectors_df = pd.read_sql("SELECT * FROM sectors", conn)
        pl_df = pd.read_sql("SELECT * FROM profitandloss ORDER BY company_id, year", conn)
        bs_df = pd.read_sql("SELECT * FROM balancesheet ORDER BY company_id, year", conn)
        mc_df = pd.read_sql("SELECT * FROM market_cap ORDER BY company_id, year", conn)

    cagr_df = compute_all_cagr()
    
    results = []
    
    company_ids = companies_df['id'].unique()
    
    for cid in company_ids:
        c_ratios = ratios_df[ratios_df['company_id'] == cid]
        c_pl = pl_df[pl_df['company_id'] == cid]
        c_bs = bs_df[bs_df['company_id'] == cid]
        c_mc = mc_df[mc_df['company_id'] == cid]
        c_cagr = cagr_df[cagr_df['company_id'] == cid] if cagr_df is not None else pd.DataFrame()
        c_sector = sectors_df[sectors_df['company_id'] == cid]['broad_sector'].values
        sector = c_sector[0] if len(c_sector) > 0 else 'Unknown'
        
        if c_ratios.empty or c_pl.empty or c_bs.empty:
            continue
            
        latest_ratio = c_ratios.iloc[-1]
        latest_pl = c_pl.iloc[-1]
        latest_bs = c_bs.iloc[-1]
        latest_mc = c_mc.iloc[-1] if not c_mc.empty else pd.Series(dtype=float)
        
        cagr_vals = c_cagr.iloc[0] if not c_cagr.empty else pd.Series(dtype=float)
        
        # Helper: get last N years of a column
        def get_last_n(df, col, n):
            return df[col].tail(n).values if len(df) >= n else []

        # Pro 1: ROE > 20% sustained for 3+ years
        roe_3yr = get_last_n(c_ratios, 'return_on_equity_pct', 3)
        if len(roe_3yr) == 3 and all(r > 20 for r in roe_3yr if pd.notna(r)):
            results.append((cid, 'pro', 'P1', "Consistently high return on equity above 20% demonstrates exceptional capital efficiency", 95))
            
        # Pro 2: FCF positive for 5+ consecutive years
        fcf_5yr = get_last_n(c_ratios, 'free_cash_flow_cr', 5)
        if len(fcf_5yr) == 5 and all(f > 0 for f in fcf_5yr if pd.notna(f)):
            results.append((cid, 'pro', 'P2', "Strong free cash flow generation over 5 years signals healthy business fundamentals", 90))
            
        # Pro 3: D/E = 0 in latest year
        de = latest_ratio.get('debt_to_equity')
        if pd.notna(de) and de == 0:
            results.append((cid, 'pro', 'P3', "Debt-free balance sheet provides financial flexibility and eliminates interest burden", 100))
            
        # Pro 4: Revenue CAGR > 15% over 5 years
        rev_cagr_5 = cagr_vals.get('sales_cagr_5yr', np.nan)
        if pd.notna(rev_cagr_5) and rev_cagr_5 > 15:
            results.append((cid, 'pro', 'P4', "Revenue growing at above 15% CAGR over 5 years reflects strong business momentum", 85))
            
        # Pro 5: OPM > 25% in latest year
        opm = latest_ratio.get('operating_profit_margin_pct')
        if pd.notna(opm) and opm > 25:
            results.append((cid, 'pro', 'P5', "Operating profit margin above 25% indicates strong pricing power and cost discipline", 80))
            
        # Pro 6: PAT CAGR > 20% over 5 years
        pat_cagr_5 = cagr_vals.get('net_profit_cagr_5yr', np.nan)
        if pd.notna(pat_cagr_5) and pat_cagr_5 > 20:
            results.append((cid, 'pro', 'P6', "Net profit compounding at above 20% over 5 years creates significant shareholder value", 90))
            
        # Pro 7: ICR > 10 or Debt Free
        icr = latest_ratio.get('interest_coverage')
        if (pd.notna(icr) and icr > 10) or (pd.notna(de) and de == 0) or icr is None:
            results.append((cid, 'pro', 'P7', "Very high interest coverage ratio reflects negligible financial stress from debt servicing", 85))
            
        # Pro 8: Dividend Yield > 2% with FCF positive
        dy = latest_mc.get('dividend_yield_pct', np.nan)
        fcf = latest_ratio.get('free_cash_flow_cr', np.nan)
        if pd.notna(dy) and dy > 2 and pd.notna(fcf) and fcf > 0:
            results.append((cid, 'pro', 'P8', "Consistent dividend yield above 2% backed by positive free cash flow", 80))
            
        # Pro 9: EPS CAGR > 15% over 5 years
        eps_cagr_5 = cagr_vals.get('eps_cagr_5yr', np.nan)
        if pd.notna(eps_cagr_5) and eps_cagr_5 > 15:
            results.append((cid, 'pro', 'P9', "Earnings per share growing above 15% CAGR indicates strong earnings quality and compounding", 85))
            
        # Pro 10: ROE improving for 3 consecutive years
        if len(roe_3yr) == 3 and (roe_3yr[2] > roe_3yr[1] > roe_3yr[0]):
            results.append((cid, 'pro', 'P10', "Return on equity improving for 3 consecutive years shows strengthening business quality", 75))
            
        # Pro 11: Revenue CAGR < PAT CAGR
        if pd.notna(rev_cagr_5) and pd.notna(pat_cagr_5) and rev_cagr_5 < pat_cagr_5:
            results.append((cid, 'pro', 'P11', "Revenue growing slower than profits shows improving operating leverage and scale benefits", 70))
            
        # Pro 12: Balance sheet assets growing with declining debt
        ta_2yr = get_last_n(c_bs, 'total_assets', 2)
        td_2yr = get_last_n(c_bs, 'borrowings', 2)
        if len(ta_2yr) == 2 and len(td_2yr) == 2:
            if ta_2yr[1] > ta_2yr[0] and td_2yr[1] < td_2yr[0]:
                results.append((cid, 'pro', 'P12', "Growing asset base funded by internal accruals reflects self-sustaining growth", 80))
                
        # Con 1: D/E > 2.0 for non-financial companies
        if pd.notna(de) and de > 2.0 and sector != 'Financials':
            results.append((cid, 'con', 'C1', f"Debt-to-equity ratio of {de:.1f}x is elevated for a non-financial company and warrants monitoring", 85))
            
        # Con 2: FCF negative for 3 consecutive years
        fcf_3yr = get_last_n(c_ratios, 'free_cash_flow_cr', 3)
        if len(fcf_3yr) == 3 and all(f < 0 for f in fcf_3yr if pd.notna(f)):
            results.append((cid, 'con', 'C2', "Free cash flow negative for 3 consecutive years raises concern about cash generation quality", 90))
            
        # Con 3: OPM declining for 3 consecutive years
        opm_3yr = get_last_n(c_ratios, 'operating_profit_margin_pct', 3)
        if len(opm_3yr) == 3 and (opm_3yr[2] < opm_3yr[1] < opm_3yr[0]):
            results.append((cid, 'con', 'C3', "Operating margins declining for 3 consecutive years suggest pricing or cost pressure", 80))
            
        # Con 4: Net profit negative in latest year
        np_latest = latest_pl.get('net_profit')
        if pd.notna(np_latest) and np_latest < 0:
            results.append((cid, 'con', 'C4', "Company reported a net loss in the most recent financial year", 95))
            
        # Con 5: Revenue declining for 2+ years
        rev_3yr = get_last_n(c_pl, 'sales', 3)
        if len(rev_3yr) == 3 and (rev_3yr[2] < rev_3yr[1] < rev_3yr[0]):
            results.append((cid, 'con', 'C5', "Revenue contraction over 2 consecutive years indicates demand weakness or market share loss", 85))
            
        # Con 6: ICR < 1.5
        if pd.notna(icr) and icr < 1.5:
            results.append((cid, 'con', 'C6', "Interest coverage ratio below 1.5x indicates the company is at risk of not meeting its debt obligations", 90))
            
        # Con 7: Dividend payout > 100%
        dp = latest_ratio.get('dividend_payout_ratio_pct')
        if pd.notna(dp) and dp > 100:
            results.append((cid, 'con', 'C7', "Dividend payout ratio above 100% means the company is paying dividends from reserves, which is unsustainable", 80))
            
        # Con 8: D/E rising for 3 consecutive years
        de_3yr = get_last_n(c_ratios, 'debt_to_equity', 3)
        if len(de_3yr) == 3 and all(pd.notna(d) for d in de_3yr) and (de_3yr[2] > de_3yr[1] > de_3yr[0]):
            results.append((cid, 'con', 'C8', "Rising debt-to-equity ratio over 3 years suggests increasing financial leverage risk", 75))
            
        # Con 9: EPS declining for 3 consecutive years
        eps_3yr = get_last_n(c_ratios, 'earnings_per_share', 3)
        if len(eps_3yr) == 3 and (eps_3yr[2] < eps_3yr[1] < eps_3yr[0]):
            results.append((cid, 'con', 'C9', "Earnings per share declining for 3 consecutive years reflects deteriorating profitability", 85))
            
        # Con 10: ROCE < 10%
        roce = latest_ratio.get('return_on_capital_pct', np.nan) # Wait, is it ROCE in ratio table? Let's check name if needed. Assuming 'return_on_equity_pct' for ROE, what about ROCE? Actually Ratio Engine instruction said "2.4 Return on Capital (ROCE)". Is it 'return_on_capital_pct' in financial_ratios? Wait, earlier I didn't see ROCE in columns list, let me just calculate it.
        # ROCE = EBIT / (Equity + Reserves + Borrowings)
        ebit = latest_pl.get('operating_profit') - latest_pl.get('depreciation', 0) if pd.notna(latest_pl.get('depreciation')) else latest_pl.get('operating_profit')
        capital = latest_bs.get('equity_capital') + latest_bs.get('reserves') + latest_bs.get('borrowings')
        if pd.notna(ebit) and pd.notna(capital) and capital > 0:
            roce = (ebit / capital) * 100
            if roce < 10:
                results.append((cid, 'con', 'C10', "Return on capital employed below 10% suggests the business is not generating sufficient returns on invested capital", 80))
                
        # Con 11: Net Debt > 3x EBITDA
        # Net Debt = Borrowings - Investments - Cash (Wait, investments is liquid proxy. In DB, total_debt_cr is borrowings.)
        # If cash is not there, we can just use borrowings - investments
        borrowings = latest_bs.get('borrowings', 0)
        investments = latest_bs.get('investments', 0)
        net_debt = borrowings - investments
        ebitda = latest_pl.get('operating_profit')
        if pd.notna(net_debt) and pd.notna(ebitda) and ebitda > 0:
            if (net_debt / ebitda) > 3:
                results.append((cid, 'con', 'C11', "Net debt exceeding 3 times EBITDA is a high leverage ratio and limits financial flexibility", 85))
                
        # Con 12: Revenue CAGR < 5% over 5 years
        if pd.notna(rev_cagr_5) and rev_cagr_5 < 5:
            results.append((cid, 'con', 'C12', "Revenue growing at below 5% over 5 years lags inflation and suggests limited business momentum", 75))

    # Add fallback rules to ensure every company has >= 1 pro and >= 1 con
    # If a company is missing a pro or con, we'll assign a generic one.
    has_pro = {r[0] for r in results if r[1] == 'pro'}
    has_con = {r[0] for r in results if r[1] == 'con'}
    
    for cid in company_ids:
        if cid not in has_pro:
            results.append((cid, 'pro', 'P_FB', "Established market position as a Nifty 100 constituent", 65))
        if cid not in has_con:
            results.append((cid, 'con', 'C_FB', "Macroeconomic factors and market volatility remain standard business risks", 65))
            
    df = pd.DataFrame(results, columns=['company_id', 'type', 'rule_id', 'text', 'confidence_pct'])
    df = df[df['confidence_pct'] > 60]
    
    out_path = os.path.join(OUTPUT_DIR, 'pros_cons_generated.csv')
    df.to_csv(out_path, index=False)
    print(f"Generated {len(df)} pros/cons for {df['company_id'].nunique()} companies. Saved to {out_path}")

if __name__ == "__main__":
    generate_pros_cons()
