import pytest
import numpy as np
from app.ml.threshold_evaluation import clopper_pearson_upper_bound, evaluate_threshold_candidates
from app.ml.feature_engineering import compute_jaccard_similarity, compute_relative_length_diff

def test_clopper_pearson_bounds():
    # 0 false hits out of 10 hits at 95% confidence
    ucb_0 = clopper_pearson_upper_bound(0, 10, confidence=0.95)
    assert ucb_0 < 0.30
    assert ucb_0 > 0.0

    # 10 false hits out of 10 hits
    ucb_10 = clopper_pearson_upper_bound(10, 10, confidence=0.95)
    assert ucb_10 == 1.0

    # 0 false hits out of 300 hits
    ucb_large = clopper_pearson_upper_bound(0, 300, confidence=0.95)
    assert ucb_large < 0.01  # Narrows below 1% with sufficient sample size

def test_feature_engineering_metrics():
    jaccard = compute_jaccard_similarity("how many leave days", "leave days available")
    assert jaccard > 0.3

    rel_diff = compute_relative_length_diff("short query", "this is a significantly longer query string")
    assert rel_diff > 0.5
