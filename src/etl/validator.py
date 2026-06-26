"""
validator.py — Data Quality Validation Module
Nifty 100 Financial Intelligence Platform
Sprint 1 — Data Foundation

This module runs 14 data quality rules against all core datasets
and generates validation_failures.csv documenting all violations
with severity levels (CRITICAL/WARNING).

Usage:
    from src.etl.validator import run_all_validations
    run_all_validations()
"""

import pandas as pd
import re
import os
import sys

# ── Path Configuration ────────────────────────────────────────────────────────

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(PROJECT_PATH)
os.chdir(PROJECT_PATH)

FAILURES_PATH = 'output/validation_failures.csv'

# ── Violation Tracker ─────────────────────────────────────────────────────────

violations = []

def log_violation(rule_id, rule_name, company_id, year, field, issue, severity):
    """
    Logs a single data quality violation to the tracker.

    Args:
        rule_id:    Rule identifier e.g. 'DQ-01'
        rule_name:  Human readable rule name
        company_id: Affected company NSE ticker
        year:       Affected year in YYYY-MM format
        field:      Affected column name
        issue:      Description of the violation
        severity:   'CRITICAL' or 'WARNING'
    """
    violations.append({
        'rule_id':    rule_id,
        'rule_name':  rule_name,
        'company_id': company_id,
        'year':       year,
        'field':      field,
        'issue':      issue,
        'severity':   severity
    })


# ── Individual DQ Rules ───────────────────────────────────────────────────────

def check_dq01_company_pk(companies):
    """DQ-01: Company primary key must be unique."""
    print("Running DQ-01: Company PK Uniqueness...")
    dupes = companies[companies['id'].duplicated()]
    if len(dupes) > 0:
        print(f"  ❌ {len(dupes)} duplicate company IDs found!")
        for _, row in dupes.iterrows():
            log_violation('DQ-01', 'Company PK Uniqueness',
                          row['id'], None, 'id',
                          'Duplicate company ticker found', 'CRITICAL')
    else:
        print(f"  ✅ All {len(companies)} company IDs are unique")


def check_dq02_annual_pk(pl, bs, cf):
    """DQ-02: No duplicate (company_id, year) pairs in time-series tables."""
    print("Running DQ-02: Annual PK Uniqueness...")
    for table_name, df in [('profitandloss', pl),
                            ('balancesheet', bs),
                            ('cashflow', cf)]:
        dupes = df[df.duplicated(subset=['company_id', 'year'])]
        if len(dupes) > 0:
            print(f"  ❌ {table_name}: {len(dupes)} duplicate rows")
            for _, row in dupes.iterrows():
                log_violation('DQ-02', 'Annual PK Uniqueness',
                              row['company_id'], row['year'],
                              'company_id+year',
                              f'Duplicate row in {table_name}', 'CRITICAL')
        else:
            print(f"  ✅ {table_name}: No duplicates found")


def check_dq03_fk_integrity(pl, bs, cf, companies):
    """DQ-03: All company_ids in child tables must exist in companies table."""
    print("Running DQ-03: Foreign Key Integrity...")
    valid_ids = set(companies['id'].unique())
    for table_name, df in [('profitandloss', pl),
                            ('balancesheet', bs),
                            ('cashflow', cf)]:
        orphans = df[~df['company_id'].isin(valid_ids)]
        if len(orphans) > 0:
            print(f"  ⚠️  {table_name}: {len(orphans)} orphan rows "
                  f"({orphans['company_id'].nunique()} companies)")
            for _, row in orphans.iterrows():
                log_violation('DQ-03', 'FK Integrity',
                              row['company_id'], row.get('year'),
                              'company_id',
                              'company_id not in companies table', 'CRITICAL')
        else:
            print(f"  ✅ {table_name}: All company IDs valid")

    # Document the finding
    print()
    print("  DQ-03 NOTE: 8 valid Nifty 100 companies missing from")
    print("  companies.xlsx master file. This is a source data gap.")
    print("  Affected: ULTRACEMCO, UNIONBANK, UNITDSPR, VBL,")
    print("            VEDL, WIPRO, ZOMATO, ZYDUSLIFE")


def check_dq04_bs_balance(bs):
    """DQ-04: Total assets must equal total liabilities within 1%."""
    print("Running DQ-04: Balance Sheet Balance...")
    bs_check = bs.copy()
    bs_check['diff_pct'] = abs(
        bs_check['total_assets'] - bs_check['total_liabilities']
    ) / bs_check['total_assets'].replace(0, float('nan')) * 100

    issues = bs_check[bs_check['diff_pct'] > 1.0]
    if len(issues) > 0:
        print(f"  ⚠️  {len(issues)} rows where assets ≠ liabilities")
        for _, row in issues.iterrows():
            log_violation('DQ-04', 'Balance Sheet Balance',
                          row['company_id'], row['year'], 'total_assets',
                          f"Diff: {row['diff_pct']:.2f}%", 'WARNING')
    else:
        print("  ✅ All balance sheets balanced")


def check_dq05_opm(pl):
    """DQ-05: OPM in source must match computed OPM within 1%."""
    print("Running DQ-05: OPM Cross Check...")
    pl_check = pl.copy()
    pl_check['computed_opm'] = (
        pl_check['operating_profit'] /
        pl_check['sales'].replace(0, float('nan')) * 100
    )
    pl_check['opm_diff'] = abs(
        pl_check['opm_percentage'] - pl_check['computed_opm']
    )
    issues = pl_check[pl_check['opm_diff'] > 1.0]
    if len(issues) > 0:
        print(f"  ⚠️  {len(issues)} rows where OPM doesn't match")
        for _, row in issues.iterrows():
            log_violation('DQ-05', 'OPM Cross Check',
                          row['company_id'], row['year'], 'opm_percentage',
                          f"OPM diff: {row['opm_diff']:.2f}%", 'WARNING')
    else:
        print("  ✅ All OPM values match computed values")


def check_dq06_positive_sales(pl):
    """DQ-06: Sales must be greater than zero."""
    print("Running DQ-06: Positive Sales...")
    issues = pl[pl['sales'] <= 0]
    if len(issues) > 0:
        print(f"  ⚠️  {len(issues)} rows with zero or negative sales")
        for _, row in issues.iterrows():
            log_violation('DQ-06', 'Positive Sales',
                          row['company_id'], row['year'], 'sales',
                          f"Sales value: {row['sales']}", 'WARNING')
    else:
        print("  ✅ All sales values are positive")


def check_dq07_year_format(pl):
    """DQ-07: All year values must match YYYY-MM format."""
    print("Running DQ-07: Year Format...")
    issues = pl[~pl['year'].str.match(r'^\d{4}-\d{2}$', na=False)]
    if len(issues) > 0:
        print(f"  ❌ {len(issues)} rows with invalid year format")
        for _, row in issues.iterrows():
            log_violation('DQ-07', 'Year Format',
                          row['company_id'], row['year'], 'year',
                          f"Invalid format: {row['year']}", 'CRITICAL')
    else:
        print("  ✅ All year formats are valid")


def check_dq08_ticker_format(companies):
    """DQ-08: Ticker length must be between 2 and 12 characters."""
    print("Running DQ-08: Ticker Format...")
    issues = companies[
        (companies['id'].str.len() < 2) |
        (companies['id'].str.len() > 12)
    ]
    if len(issues) > 0:
        print(f"  ⚠️  {len(issues)} tickers with invalid length")
        for _, row in issues.iterrows():
            log_violation('DQ-08', 'Ticker Format',
                          row['id'], None, 'id',
                          f"Invalid length: {row['id']}", 'CRITICAL')
    else:
        print("  ✅ All ticker formats are valid")


def check_dq09_net_cash(cf):
    """DQ-09: Net cash flow must equal CFO + CFI + CFF within 10 Cr."""
    print("Running DQ-09: Net Cash Check...")
    cf_check = cf.copy()
    cf_check['computed_net'] = (
        cf_check['operating_activity'] +
        cf_check['investing_activity'] +
        cf_check['financing_activity']
    )
    cf_check['cash_diff'] = abs(
        cf_check['net_cash_flow'] - cf_check['computed_net']
    )
    issues = cf_check[cf_check['cash_diff'] > 10]
    if len(issues) > 0:
        print(f"  ⚠️  {len(issues)} rows where net cash doesn't match")
        for _, row in issues.iterrows():
            log_violation('DQ-09', 'Net Cash Check',
                          row['company_id'], row['year'], 'net_cash_flow',
                          f"Diff: {row['cash_diff']:.0f} Cr", 'WARNING')
    else:
        print("  ✅ All net cash flow values match")


def check_dq10_fixed_assets(bs):
    """DQ-10: Fixed assets must be non-negative."""
    print("Running DQ-10: Non-Negative Fixed Assets...")
    issues = bs[bs['fixed_assets'] < 0]
    if len(issues) > 0:
        print(f"  ⚠️  {len(issues)} rows with negative fixed assets")
        for _, row in issues.iterrows():
            log_violation('DQ-10', 'Non-Negative Fixed Assets',
                          row['company_id'], row['year'], 'fixed_assets',
                          f"Value: {row['fixed_assets']}", 'WARNING')
    else:
        print("  ✅ All fixed asset values are non-negative")


def check_dq11_tax_rate(pl):
    """DQ-11: Tax rate must be between 0% and 60%."""
    print("Running DQ-11: Tax Rate Range...")
    issues = pl[
        (pl['tax_percentage'] < 0) |
        (pl['tax_percentage'] > 60)
    ]
    if len(issues) > 0:
        print(f"  ⚠️  {len(issues)} rows with unusual tax rate")
        for _, row in issues.iterrows():
            log_violation('DQ-11', 'Tax Rate Range',
                          row['company_id'], row['year'], 'tax_percentage',
                          f"Tax rate: {row['tax_percentage']}%", 'WARNING')
    else:
        print("  ✅ All tax rates are within range")


def check_dq12_dividend_payout(pl):
    """DQ-12: Dividend payout above 200% is likely a data error."""
    print("Running DQ-12: Dividend Payout Cap...")
    issues = pl[pl['dividend_payout'] > 200]
    if len(issues) > 0:
        print(f"  ⚠️  {len(issues)} rows with unusually high dividend payout")
        for _, row in issues.iterrows():
            log_violation('DQ-12', 'Dividend Payout Cap',
                          row['company_id'], row['year'], 'dividend_payout',
                          f"Payout: {row['dividend_payout']}%", 'WARNING')
    else:
        print("  ✅ All dividend payout values within range")


def check_dq14_eps_sign(pl):
    """DQ-14: EPS must be positive if net profit is positive."""
    print("Running DQ-14: EPS Sign Consistency...")
    issues = pl[(pl['net_profit'] > 0) & (pl['eps'] <= 0)]
    if len(issues) > 0:
        print(f"  ⚠️  {len(issues)} rows where profit positive but EPS not")
        for _, row in issues.iterrows():
            log_violation('DQ-14', 'EPS Sign Consistency',
                          row['company_id'], row['year'], 'eps',
                          f"Profit: {row['net_profit']}, EPS: {row['eps']}",
                          'WARNING')
    else:
        print("  ✅ All EPS values consistent with net profit")


def check_dq16_coverage(pl):
    """DQ-16: Each company must have at least 5 years of P&L data."""
    print("Running DQ-16: Coverage Check...")
    coverage    = pl.groupby('company_id')['year'].count()
    low_coverage = coverage[coverage < 5]
    if len(low_coverage) > 0:
        print(f"  ⚠️  {len(low_coverage)} companies with less than 5 years")
        for company_id, count in low_coverage.items():
            log_violation('DQ-16', 'Coverage Check',
                          company_id, None, 'year',
                          f"Only {count} years available", 'WARNING')
    else:
        print("  ✅ All companies have 5+ years of data")


# ── Save Report ───────────────────────────────────────────────────────────────

def save_violations_report():
    """
    Saves all logged violations to validation_failures.csv.
    Always creates the file even if there are zero violations.

    Returns:
        DataFrame: The violations report
    """
    violations_df = pd.DataFrame(violations) if violations else pd.DataFrame(
        columns=['rule_id', 'rule_name', 'company_id',
                 'year', 'field', 'issue', 'severity']
    )

    violations_df.to_csv(FAILURES_PATH, index=False)

    print(f"\nvalidation_failures.csv saved — {len(violations_df)} violations")

    if len(violations_df) > 0:
        print("\nSummary by severity:")
        print(violations_df['severity'].value_counts().to_string())
        print("\nSummary by rule:")
        print(violations_df['rule_id'].value_counts().to_string())

    return violations_df


# ── Master Validator ──────────────────────────────────────────────────────────

def run_all_validations():
    """
    Runs all 14 DQ rules and saves validation_failures.csv.

    Usage:
        from src.etl.validator import run_all_validations
        run_all_validations()
    """
    from src.etl.loader import load_all_data

    # Load clean data
    data      = load_all_data()
    pl        = data['profitandloss']
    bs        = data['balancesheet']
    cf        = data['cashflow']
    companies = data['companies']

    print("\n" + "=" * 50)
    print("Running Data Quality Validation — 14 Rules")
    print("=" * 50 + "\n")

    # Run all rules
    check_dq01_company_pk(companies)
    check_dq02_annual_pk(pl, bs, cf)
    check_dq03_fk_integrity(pl, bs, cf, companies)
    check_dq04_bs_balance(bs)
    check_dq05_opm(pl)
    check_dq06_positive_sales(pl)
    check_dq07_year_format(pl)
    check_dq08_ticker_format(companies)
    check_dq09_net_cash(cf)
    check_dq10_fixed_assets(bs)
    check_dq11_tax_rate(pl)
    check_dq12_dividend_payout(pl)
    check_dq14_eps_sign(pl)
    check_dq16_coverage(pl)

    # Save report
    print("\n" + "=" * 50)
    return save_violations_report()


# ── Run directly for testing ──────────────────────────────────────────────────

if __name__ == "__main__":
    run_all_validations()
