"""
test_cagr.py — Unit Tests for CAGR Formula
Tests all edge cases in the CAGR computation function.
"""

import sys
import os
import pytest

project_path = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(project_path)
os.chdir(project_path)

from src.analytics.cagr import compute_cagr


def test_cagr_normal():
    """Normal CAGR computation should work correctly."""
    cagr, flag = compute_cagr(100, 161.05, 5)
    assert abs(cagr - 10.0) < 0.1
    assert flag == 'OK'

def test_cagr_turnaround():
    """CAGR should be None for turnaround (negative to positive)."""
    cagr, flag = compute_cagr(-100, 200, 5)
    assert cagr is None
    assert flag == 'TURNAROUND'

def test_cagr_decline_to_loss():
    """CAGR should be None for decline to loss (positive to negative)."""
    cagr, flag = compute_cagr(100, -200, 5)
    assert cagr is None
    assert flag == 'DECLINE_TO_LOSS'

def test_cagr_both_negative():
    """CAGR should be None when both values are negative."""
    cagr, flag = compute_cagr(-100, -50, 5)
    assert cagr is None
    assert flag == 'BOTH_NEGATIVE'

def test_cagr_zero_base():
    """CAGR should be None when base value is zero."""
    cagr, flag = compute_cagr(0, 200, 5)
    assert cagr is None
    assert flag == 'ZERO_BASE'

def test_cagr_insufficient_history():
    """CAGR should be None when n_years is less than 3."""
    cagr, flag = compute_cagr(100, 200, 2)
    assert cagr is None
    assert flag == 'INSUFFICIENT'

def test_cagr_exactly_3_years():
    """CAGR should compute normally for exactly 3 years."""
    cagr, flag = compute_cagr(100, 133.1, 3)
    assert abs(cagr - 10.0) < 0.1
    assert flag == 'OK'

def test_cagr_zero_growth():
    """CAGR should be 0 when start and end values are equal."""
    cagr, flag = compute_cagr(100, 100, 5)
    assert cagr == 0.0
    assert flag == 'OK'