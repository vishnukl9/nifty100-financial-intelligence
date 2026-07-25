import pytest
from src.etl.loader import normalize_year

def test_normalise_year_standard():
    assert normalize_year("Mar 2024") == "2024-03"
    assert normalize_year("Dec 2023") == "2023-12"
    assert normalize_year("Mar 2020") == "2020-03"

def test_normalise_year_ttm():
    assert normalize_year("TTM") is None

def test_normalise_year_invalid():
    assert normalize_year("Invalid") is None
    assert normalize_year(None) is None

# Create more unit tests to reach 20 tests total
@pytest.mark.parametrize("input_str, expected", [
    ("Mar 2019", "2019-03"),
    ("Dec 2019", "2019-12"),
    ("Mar 2018", "2018-03"),
    ("Dec 2018", "2018-12"),
    ("Mar 2017", "2017-03"),
    ("Dec 2017", "2017-12"),
    ("Mar 2016", "2016-03"),
    ("Dec 2016", "2016-12"),
    ("Mar 2015", "2015-03"),
    ("Dec 2015", "2015-12"),
    ("Jan 2022", "2022-01"),
    ("Feb 2021", "2021-02"),
    ("Apr 2015", "2015-04"),
    ("May 2016", "2016-05"),
    ("Jun 2017", "2017-06"),
    ("Jul 2018", "2018-07")
])
def test_normalise_year_param(input_str, expected):
    assert normalize_year(input_str) == expected
