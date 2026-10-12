import pytest
from app.ml.policy_validation import extract_policy_conditions, validate_condition_safety, normalize_text

def test_normalization():
    assert normalize_text("  How Many   LEAVE Days?\n\t") == "how many leave days?"

def test_condition_extraction_jurisdiction():
    cond_us = extract_policy_conditions("What is the meal allowance in the US?")
    assert cond_us.jurisdiction == "US"
    assert cond_us.domain == "FINANCE"

    cond_in = extract_policy_conditions("What is the travel per diem in India?")
    assert cond_in.jurisdiction == "INDIA"
    assert cond_in.domain == "FINANCE"

def test_condition_extraction_category():
    cond_contractor = extract_policy_conditions("Do contractors get paid vacation?")
    assert cond_contractor.employee_category == "CONTRACTOR"

    cond_fte = extract_policy_conditions("How many leave days do full-time employees get?")
    assert cond_fte.employee_category == "FULL_TIME"

def test_condition_extraction_numbers():
    cond_nums = extract_policy_conditions("Can employees work remotely 2 days a week?")
    assert cond_nums.numerical_limits.get("days") == 2.0

def test_deterministic_safety_blocks_jurisdiction_mismatch():
    q_cond = extract_policy_conditions("What is the travel meal rate in the US?")
    cand_dict = {
        "domain": "FINANCE",
        "jurisdiction": "INDIA",
        "employee_category": "ALL",
        "numerical_limits": {"inr": 3000.0}
    }
    is_safe, reasons = validate_condition_safety(q_cond, cand_dict)
    assert is_safe is False
    assert any("Jurisdiction mismatch" in r for r in reasons)

def test_deterministic_safety_blocks_category_mismatch():
    q_cond = extract_policy_conditions("How many annual leave days do contractors get?")
    cand_dict = {
        "domain": "HR",
        "jurisdiction": "GLOBAL",
        "employee_category": "FULL_TIME",
        "numerical_limits": {"days": 20.0}
    }
    is_safe, reasons = validate_condition_safety(q_cond, cand_dict)
    assert is_safe is False
    assert any("Employee category mismatch" in r for r in reasons)

def test_deterministic_safety_blocks_numerical_mismatch():
    q_cond = extract_policy_conditions("Can I work from home 4 days a week?")
    cand_dict = {
        "domain": "HR",
        "jurisdiction": "GLOBAL",
        "employee_category": "FULL_TIME",
        "numerical_limits": {"days": 2.0}
    }
    is_safe, reasons = validate_condition_safety(q_cond, cand_dict)
    assert is_safe is False
    assert any("Numerical limit mismatch" in r for r in reasons)

def test_deterministic_safety_allows_matching_conditions():
    q_cond = extract_policy_conditions("How many vacation days do permanent employees receive?")
    cand_dict = {
        "domain": "HR",
        "jurisdiction": "GLOBAL",
        "employee_category": "FULL_TIME",
        "numerical_limits": {}
    }
    is_safe, reasons = validate_condition_safety(q_cond, cand_dict)
    assert is_safe is True
    assert len(reasons) == 0
