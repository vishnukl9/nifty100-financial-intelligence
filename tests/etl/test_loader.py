import pytest
import os
from src.etl.loader import load_all_data

def test_load_all_data_keys():
    data = load_all_data()
    expected_keys = [
        "profitandloss", "balancesheet", "cashflow", "companies", 
        "analysis", "documents", "prosandcons", "sectors", 
        "market_cap", "financial_ratios", "peer_groups"
    ]
    for key in expected_keys:
        assert key in data

def test_load_companies_shape():
    data = load_all_data()
    assert len(data['companies']) == 92
    
def test_load_ratios_shape():
    data = load_all_data()
    assert len(data['financial_ratios']) >= 920 # roughly 10 years per company
    
# More loader tests
@pytest.mark.parametrize("dataset, min_rows", [
    ("profitandloss", 900),
    ("balancesheet", 900),
    ("cashflow", 900),
    ("sectors", 92),
    ("market_cap", 400),
])
def test_load_dataset_min_rows(dataset, min_rows):
    data = load_all_data()
    assert len(data[dataset]) >= min_rows

def test_loader_columns_exist():
    data = load_all_data()
    assert 'company_id' in data['profitandloss'].columns
    assert 'year' in data['profitandloss'].columns

def test_loader_no_duplicates():
    data = load_all_data()
    assert not data['companies']['id'].duplicated().any()
