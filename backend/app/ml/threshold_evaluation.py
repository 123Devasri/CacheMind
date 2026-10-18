import numpy as np
from typing import List, Dict, Any, Tuple
from scipy.stats import beta

def clopper_pearson_upper_bound(k: int, n: int, confidence: float = 0.95) -> float:
    """
    Computes exact Clopper-Pearson binomial one-sided upper confidence bound for success rate p.
    For False-Hit Rate (FHR), k is the number of false hits, n is the total number of cache hits evaluated.
    Returns: UCB in [0, 1].
    """
    if n == 0:
        return 1.0
    if k == n:
        return 1.0
    
    # 1-sided (1 - alpha) bound corresponds to beta distribution quantile
    alpha = 1.0 - confidence
    # Upper bound = beta.ppf(1 - alpha, k + 1, n - k)
    ucb = beta.ppf(1.0 - alpha, k + 1, n - k)
    return float(min(max(ucb, 0.0), 1.0))

def evaluate_threshold_candidates(
    calibrated_scores: np.ndarray,
    y_true: np.ndarray,
    target_fhr: float = 0.01,
    confidence_level: float = 0.95,
    threshold_steps: int = 50
) -> Dict[str, Any]:
    """
    Evaluates candidate acceptance thresholds tau in [0.5, 0.99].
    False-Hit Rate (FHR) is defined as:
        FHR = (Number of false hits where tau was met but true_label == 0) / (Total cache decisions where score >= tau)
    Computes Clopper-Pearson one-sided upper confidence bound (UCB).
    Selects the lowest threshold tau such that UCB <= target_fhr (or lowest observed FHR if none strictly meets target).
    """
    n_samples = len(calibrated_scores)
    if n_samples == 0:
        return {
            "status": "insufficient_data",
            "message": "No validation samples available.",
            "selected_threshold": 0.95,
            "results": []
        }

    candidate_taus = np.linspace(0.50, 0.99, threshold_steps)
    results = []
    
    selected_tau = None
    conservative_fallback = 0.95

    for tau in candidate_taus:
        tau_val = float(round(tau, 3))
        hits_mask = (calibrated_scores >= tau_val)
        n_hits = int(np.sum(hits_mask))
        
        if n_hits == 0:
            observed_fhr = 0.0
            ucb = 1.0 # Undefined/unsupported without hits
        else:
            false_hits = int(np.sum((y_true[hits_mask] == 0)))
            observed_fhr = float(false_hits / n_hits)
            ucb = clopper_pearson_upper_bound(false_hits, n_hits, confidence=confidence_level)

        rec = {
            "threshold": tau_val,
            "evaluated_hits": n_hits,
            "false_hits": int(np.sum((y_true[hits_mask] == 0))) if n_hits > 0 else 0,
            "observed_fhr": observed_fhr,
            "upper_confidence_bound": ucb,
            "meets_target": bool(ucb <= target_fhr and n_hits >= 10)
        }
        results.append(rec)
        
        # We want the lowest threshold that statistically guarantees UCB <= target_fhr
        if selected_tau is None and rec["meets_target"]:
            selected_tau = tau_val

    # If no threshold strictly has UCB <= target_fhr (common with small n because Clopper-Pearson is strict),
    # select the highest precision / lowest FHR threshold and mark conservative fallback.
    status = "passed"
    if selected_tau is None:
        status = "conservative_fallback"
        # Find threshold with lowest observed FHR that still gives hits
        valid_candidates = [r for r in results if r["evaluated_hits"] > 0]
        if valid_candidates:
            # Filter candidates that achieve the minimum observed FHR
            min_fhr = min(r["observed_fhr"] for r in valid_candidates)
            best_candidates = [r for r in valid_candidates if abs(r["observed_fhr"] - min_fhr) < 1e-5]
            # Select the median/accessible threshold among the best (defaulting around 0.50)
            selected_tau = min(best_candidates, key=lambda x: abs(x["threshold"] - 0.50))["threshold"]
        else:
            selected_tau = conservative_fallback

    # Find the stats of the selected threshold
    selected_record = next((r for r in results if r["threshold"] == selected_tau), None)

    return {
        "status": status,
        "target_fhr": target_fhr,
        "confidence_level": confidence_level,
        "selected_threshold": selected_tau,
        "sample_size": n_samples,
        "selected_stats": selected_record,
        "results": results,
        "warning": "Note: Small sample sizes yield wide Clopper-Pearson intervals; more labeled data narrows the bound." if n_samples < 100 else None
    }
