import csv
import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import ModelMetadata, ThresholdEvaluationRun
from app.ml.embeddings import embedding_service
from app.ml.policy_validation import extract_policy_conditions, normalize_text
from app.ml.feature_engineering import build_pair_features
from app.ml.equivalence_classifier import equivalence_classifier
from app.ml.probability_calibration import probability_calibrator
from app.ml.threshold_evaluation import evaluate_threshold_candidates
from app.ml.query_clustering import query_clusterer
from app.models.entities import CachedEntry

def load_dataset_split(split_name: str) -> List[Dict[str, Any]]:
    csv_path = settings.DATASETS_DIR / "enterprise_policy_pairs_split.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset file not found at {csv_path}")
    
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("split") == split_name:
                rows.append({
                    "q1": r["q1"],
                    "q2": r["q2"],
                    "label": int(r["label"]),
                    "group": r.get("group", "")
                })
    return rows

def generate_features_for_pairs(pairs: List[Dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    if not pairs:
        return np.empty((0, 8), dtype=np.float32), np.empty((0,), dtype=np.int32)
        
    X_list = []
    y_list = []

    for item in pairs:
        q1 = item["q1"]
        q2 = item["q2"]
        label = item["label"]

        q1_norm = normalize_text(q1)
        q2_norm = normalize_text(q2)

        # Embeddings
        e1 = embedding_service.encode(q1_norm, normalize=True).flatten()
        e2 = embedding_service.encode(q2_norm, normalize=True).flatten()
        cos_sim = float(np.dot(e1, e2))

        # Conditions
        c1 = extract_policy_conditions(q1_norm)
        c2 = extract_policy_conditions(q2_norm)
        c2_dict = {
            "domain": c2.domain,
            "jurisdiction": c2.jurisdiction,
            "employee_category": c2.employee_category,
            "numerical_limits": c2.numerical_limits,
            "is_negated": c2.is_negated,
            "policy_version": c2.policy_version
        }

        feats = build_pair_features(q1_norm, q2_norm, cos_sim, c1, c2_dict)
        X_list.append(feats)
        y_list.append(label)

    return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.int32)

def train_and_evaluate_all_models(db: Session) -> Dict[str, Any]:
    """
    Complete ML pipeline training & calibration workflow:
    1. Trains Logistic Regression classifier on TRAIN split only.
    2. Fits Isotonic Regression probability calibrator on separate CALIBRATION split.
    3. Evaluates thresholds on VALIDATION split with Clopper-Pearson confidence bounds.
    4. Evaluates final performance on unseen TEST split.
    5. Runs initial K-Means clustering over cache query embeddings.
    6. Persists model metadata and threshold evaluation run to DB.
    """
    print("Loading train, calibration, validation, and test splits...")
    train_pairs = load_dataset_split("train")
    cal_pairs = load_dataset_split("calibration")
    val_pairs = load_dataset_split("validation")
    test_pairs = load_dataset_split("test")

    # Fallback to combine if split sizes are too small
    if len(train_pairs) < 4:
        raise ValueError("Insufficient training pairs in dataset.")

    # 1. Train Classifier
    print(f"Training Logistic Regression on {len(train_pairs)} training pairs...")
    X_train, y_train = generate_features_for_pairs(train_pairs)
    train_res = equivalence_classifier.train(X_train, y_train, C=1.0)

    # 2. Fit Isotonic Calibrator
    print(f"Fitting Isotonic Regression on {len(cal_pairs)} calibration pairs...")
    X_cal, y_cal = generate_features_for_pairs(cal_pairs)
    # Get raw scores from trained classifier
    raw_cal_scores = np.array([equivalence_classifier.predict_score(x) for x in X_cal])
    cal_res = probability_calibrator.fit(raw_cal_scores, y_cal)

    # 3. Evaluate Thresholds on Validation split
    print(f"Evaluating statistical thresholds on {len(val_pairs)} validation pairs...")
    X_val, y_val = generate_features_for_pairs(val_pairs)
    raw_val_scores = np.array([equivalence_classifier.predict_score(x) for x in X_val])
    cal_val_scores = np.array([probability_calibrator.calibrate(s) for s in raw_val_scores])

    thresh_eval = evaluate_threshold_candidates(
        cal_val_scores,
        y_val,
        target_fhr=settings.TARGET_FHR,
        confidence_level=settings.CONFIDENCE_LEVEL
    )

    # 4. Evaluate Final Performance on Test Split
    print(f"Evaluating final generalization on {len(test_pairs)} test pairs...")
    X_test, y_test = generate_features_for_pairs(test_pairs)
    raw_test_scores = np.array([equivalence_classifier.predict_score(x) for x in X_test])
    cal_test_scores = np.array([probability_calibrator.calibrate(s) for s in raw_test_scores])
    
    sel_tau = thresh_eval["selected_threshold"]
    test_hits = (cal_test_scores >= sel_tau)
    test_n_hits = int(np.sum(test_hits))
    test_false_hits = int(np.sum((y_test[test_hits] == 0))) if test_n_hits > 0 else 0
    test_observed_fhr = float(test_false_hits / test_n_hits) if test_n_hits > 0 else 0.0

    # 5. Run initial K-Means clustering on cached entries
    cached_entries = db.query(CachedEntry).filter(CachedEntry.is_active == True).all()
    questions = [c.question for c in cached_entries]
    if len(questions) >= 2:
        embs = embedding_service.encode([c.normalized_question for c in cached_entries], normalize=True)
        clustering_res = query_clusterer.cluster_queries(questions, embs, n_clusters=3)
    else:
        clustering_res = {"status": "insufficient_data"}

    # 6. Save DB Records
    # Classifier Metadata
    meta_clf = db.query(ModelMetadata).filter(ModelMetadata.model_name == "equivalence_classifier").first()
    if not meta_clf:
        meta_clf = ModelMetadata(model_name="equivalence_classifier")
        db.add(meta_clf)
    meta_clf.status = "ready"
    meta_clf.metrics = train_res["metrics"]
    meta_clf.hyperparameters = train_res["hyperparameters"]
    meta_clf.artifact_path = str(equivalence_classifier.model_path)

    # Calibrator Metadata
    meta_cal = db.query(ModelMetadata).filter(ModelMetadata.model_name == "probability_calibrator").first()
    if not meta_cal:
        meta_cal = ModelMetadata(model_name="probability_calibrator")
        db.add(meta_cal)
    meta_cal.status = "ready"
    meta_cal.metrics = {
        "brier_before": cal_res["brier_score_before"],
        "brier_after": cal_res["brier_score_after"],
        "sample_count": cal_res["sample_count"]
    }
    meta_cal.artifact_path = str(probability_calibrator.model_path)

    # Threshold evaluation record
    eval_rec = ThresholdEvaluationRun(
        target_fhr=settings.TARGET_FHR,
        confidence_level=settings.CONFIDENCE_LEVEL,
        selected_threshold=sel_tau,
        status=thresh_eval["status"],
        sample_size=thresh_eval["sample_size"],
        false_hits=thresh_eval["selected_stats"]["false_hits"] if thresh_eval["selected_stats"] else 0,
        observed_fhr=thresh_eval["selected_stats"]["observed_fhr"] if thresh_eval["selected_stats"] else 0.0,
        upper_confidence_bound=thresh_eval["selected_stats"]["upper_confidence_bound"] if thresh_eval["selected_stats"] else 1.0,
        detailed_results=thresh_eval["results"],
        dataset_version="v1.0",
        is_active=True
    )
    # Deactivate older evaluation runs
    db.query(ThresholdEvaluationRun).update({"is_active": False})
    db.add(eval_rec)
    db.commit()

    return {
        "classifier": train_res,
        "calibrator": cal_res,
        "threshold_evaluation": thresh_eval,
        "test_split_evaluation": {
            "selected_threshold": sel_tau,
            "test_sample_count": len(test_pairs),
            "test_cache_hits": test_n_hits,
            "test_false_hits": test_false_hits,
            "test_observed_fhr": test_observed_fhr
        },
        "clustering": clustering_res
    }

if __name__ == "__main__":
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        res = train_and_evaluate_all_models(db)
        print("Model training & evaluation pipeline completed successfully!")
        print(f"Selected Threshold: {res['threshold_evaluation']['selected_threshold']}")
    finally:
        db.close()
