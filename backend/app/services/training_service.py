import os
import csv
import json
import shutil
import datetime
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import ModelMetadata, ThresholdEvaluationRun, ModelArtifactVersion, CachedEntry, Policy
from app.ml.embeddings import embedding_service
from app.ml.faiss_index import faiss_service
from app.ml.policy_validation import extract_policy_conditions, normalize_text
from app.ml.feature_engineering import build_pair_features
from app.ml.equivalence_classifier import equivalence_classifier
from app.ml.probability_calibration import probability_calibrator
from app.ml.threshold_evaluation import evaluate_threshold_candidates
from app.ml.query_clustering import query_clusterer

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

    # Collect normalized texts
    norm_q1_list = [normalize_text(item["q1"]) for item in pairs]
    norm_q2_list = [normalize_text(item["q2"]) for item in pairs]

    # Batch encode all unique questions
    unique_texts = list(dict.fromkeys(norm_q1_list + norm_q2_list))
    if unique_texts:
        embs_matrix = embedding_service.encode(unique_texts, normalize=True)
        emb_lookup = {txt: embs_matrix[i].flatten() for i, txt in enumerate(unique_texts)}
    else:
        emb_lookup = {}

    X_list = []
    y_list = []

    for idx, item in enumerate(pairs):
        q1_norm = norm_q1_list[idx]
        q2_norm = norm_q2_list[idx]
        label = item["label"]

        e1 = emb_lookup.get(q1_norm)
        e2 = emb_lookup.get(q2_norm)
        if e1 is not None and e2 is not None:
            cos_sim = float(np.dot(e1, e2))
        else:
            cos_sim = 0.0

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

def train_and_evaluate_all_models(db: Session, created_by: str = "administrator") -> Dict[str, Any]:
    """
    Complete ML pipeline training & calibration workflow:
    1. Trains Logistic Regression classifier on TRAIN split only.
    2. Fits Isotonic Regression probability calibrator on separate CALIBRATION split.
    3. Evaluates thresholds on VALIDATION split with Clopper-Pearson confidence bounds.
    4. Evaluates final performance on unseen TEST split.
    5. Runs K-Means clustering over cache query embeddings.
    6. Creates atomic version snapshot in Model Registry.
    7. Persists model metadata and threshold evaluation run to DB.
    """
    # 0. Build/verify hybrid QQP + Enterprise Policy splits
    from app.services.dataset_service import build_hybrid_dataset_splits
    try:
        build_hybrid_dataset_splits(db, max_qqp=500)
    except Exception as e:
        print(f"[TrainingService] Hybrid dataset build notice: {e}")

    print("Loading train, calibration, validation, and test splits...")
    train_pairs = load_dataset_split("train")
    cal_pairs = load_dataset_split("calibration")
    val_pairs = load_dataset_split("validation")
    test_pairs = load_dataset_split("test")

    if len(train_pairs) < 4:
        raise ValueError("Insufficient training pairs in dataset.")

    # 1. Train Multi-Model Classifier Suite (Decision Tree ID3 + Logistic Regression + k-NN)
    print(f"Training Multi-Model Classifier Suite on {len(train_pairs)} training pairs...")
    X_train, y_train = generate_features_for_pairs(train_pairs)
    train_res = equivalence_classifier.train(X_train, y_train, C=1.0)

    # 2. Fit Isotonic Calibrator
    print(f"Fitting Isotonic Regression on {len(cal_pairs)} calibration pairs...")
    X_cal, y_cal = generate_features_for_pairs(cal_pairs)
    raw_cal_scores = np.array([equivalence_classifier.predict_score(x) for x in X_cal])
    cal_res = probability_calibrator.fit(raw_cal_scores, y_cal)

    # 3. Evaluate Thresholds on Validation split (using 100+ samples for tight Clopper-Pearson bound)
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

    # 5. Run K-Means query clustering (Syllabus Model: Clustering)
    cached_entries = db.query(CachedEntry).filter(CachedEntry.is_active == True).all()
    questions = [c.question for c in cached_entries]
    if len(questions) >= 2:
        embs = embedding_service.encode([c.normalized_question for c in cached_entries], normalize=True)
        clustering_res = query_clusterer.cluster_queries(questions, embs, n_clusters=min(5, len(questions)))
    else:
        clustering_res = {"status": "insufficient_data"}

    # 6. Save DB Records for Current Models
    meta_clf = db.query(ModelMetadata).filter(ModelMetadata.model_name == "equivalence_classifier").first()
    if not meta_clf:
        meta_clf = ModelMetadata(model_name="equivalence_classifier")
        db.add(meta_clf)
    meta_clf.status = "ready"
    meta_clf.metrics = train_res["metrics"]
    meta_clf.hyperparameters = train_res["hyperparameters"]
    meta_clf.artifact_path = str(equivalence_classifier.model_path)
    meta_clf.last_trained_at = datetime.datetime.utcnow()

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
    meta_cal.last_trained_at = datetime.datetime.utcnow()

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
    db.query(ThresholdEvaluationRun).update({"is_active": False})
    db.add(eval_rec)
    db.commit()

    # 7. Model Registry Snapshot Creation (For Atomic Rollback)
    version_tag = f"v1.0.{int(datetime.datetime.utcnow().timestamp())}"
    registry_dir = settings.MODELS_DIR / "registry" / version_tag
    registry_dir.mkdir(parents=True, exist_ok=True)

    clf_snapshot = registry_dir / "equivalence_classifier.joblib"
    cal_snapshot = registry_dir / "isotonic_calibrator.joblib"
    dt_snapshot = registry_dir / "decision_tree_classifier.joblib"
    knn_snapshot = registry_dir / "knn_classifier.joblib"
    idx_snapshot = registry_dir / "faiss_cache.index"
    map_snapshot = registry_dir / "faiss_id_map.json"

    # Copy artifacts to snapshot directory
    if equivalence_classifier.model_path.exists():
        shutil.copy2(equivalence_classifier.model_path, clf_snapshot)
    if probability_calibrator.model_path.exists():
        shutil.copy2(probability_calibrator.model_path, cal_snapshot)
    if (settings.MODELS_DIR / "decision_tree_classifier.joblib").exists():
        shutil.copy2(settings.MODELS_DIR / "decision_tree_classifier.joblib", dt_snapshot)
    if (settings.MODELS_DIR / "knn_classifier.joblib").exists():
        shutil.copy2(settings.MODELS_DIR / "knn_classifier.joblib", knn_snapshot)
    if faiss_service.index_file.exists():
        shutil.copy2(faiss_service.index_file, idx_snapshot)
    if faiss_service.map_file.exists():
        shutil.copy2(faiss_service.map_file, map_snapshot)

    # Deactivate older versions in registry
    db.query(ModelArtifactVersion).update({"is_active": False})

    reg_record = ModelArtifactVersion(
        version_tag=version_tag,
        classifier_path=str(clf_snapshot),
        calibrator_path=str(cal_snapshot),
        faiss_index_path=str(idx_snapshot),
        faiss_id_map_path=str(map_snapshot),
        selected_threshold=float(sel_tau),
        target_fhr=float(settings.TARGET_FHR),
        observed_fhr=thresh_eval["selected_stats"]["observed_fhr"] if thresh_eval["selected_stats"] else 0.0,
        upper_confidence_bound=thresh_eval["selected_stats"]["upper_confidence_bound"] if thresh_eval["selected_stats"] else 1.0,
        sample_size=thresh_eval["sample_size"],
        metrics={
            "classifier": train_res["metrics"],
            "decision_tree": train_res.get("decision_tree", {}).get("metrics", {}),
            "knn": train_res.get("knn", {}).get("metrics", {}),
            "calibrator": {
                "brier_before": cal_res["brier_score_before"],
                "brier_after": cal_res["brier_score_after"]
            },
            "test_split": {
                "hits": test_n_hits,
                "false_hits": test_false_hits,
                "observed_fhr": test_observed_fhr
            }
        },
        hyperparameters={
            **train_res["hyperparameters"],
            "active_model": equivalence_classifier.active_model
        },
        dataset_version="v1.0",
        is_active=True,
        created_by=created_by
    )
    db.add(reg_record)
    db.commit()

    return {
        "version_tag": version_tag,
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

def rollback_to_model_version(db: Session, target_version_tag: str) -> Dict[str, Any]:
    """
    Safely rolls back the ML pipeline and vector index to a previous working version.
    Restores model artifacts and threshold state atomically.
    """
    version_rec = db.query(ModelArtifactVersion).filter(
        ModelArtifactVersion.version_tag == target_version_tag
    ).first()

    if not version_rec:
        raise ValueError(f"Version tag {target_version_tag} not found in model registry.")

    clf_path = Path(version_rec.classifier_path)
    cal_path = Path(version_rec.calibrator_path)
    idx_path = Path(version_rec.faiss_index_path)
    map_path = Path(version_rec.faiss_id_map_path)

    if not clf_path.exists() or not cal_path.exists():
        raise FileNotFoundError(f"One or more artifact files missing for version {target_version_tag}")

    # Copy files back to active directory
    shutil.copy2(clf_path, equivalence_classifier.model_path)
    shutil.copy2(cal_path, probability_calibrator.model_path)
    dt_snapshot = clf_path.parent / "decision_tree_classifier.joblib"
    knn_snapshot = clf_path.parent / "knn_classifier.joblib"
    if dt_snapshot.exists():
        shutil.copy2(dt_snapshot, settings.MODELS_DIR / "decision_tree_classifier.joblib")
    if knn_snapshot.exists():
        shutil.copy2(knn_snapshot, settings.MODELS_DIR / "knn_classifier.joblib")
    if idx_path.exists():
        shutil.copy2(idx_path, faiss_service.index_file)
    if map_path.exists():
        shutil.copy2(map_path, faiss_service.map_file)

    # Reload memory objects
    equivalence_classifier.load()
    probability_calibrator.load()
    from app.ml.decision_tree_classifier import decision_tree_classifier
    from app.ml.knn_classifier import knn_classifier
    decision_tree_classifier.load()
    knn_classifier.load()
    faiss_service.load_or_create()

    # Update active status in DB
    db.query(ModelArtifactVersion).update({"is_active": False})
    version_rec.is_active = True

    # Activate corresponding threshold evaluation
    eval_run = db.query(ThresholdEvaluationRun).order_by(ThresholdEvaluationRun.created_at.desc()).first()
    if eval_run:
        eval_run.selected_threshold = version_rec.selected_threshold
        eval_run.is_active = True

    db.commit()

    return {
        "status": "success",
        "message": f"Successfully rolled back to version {target_version_tag}.",
        "active_version": target_version_tag,
        "selected_threshold": version_rec.selected_threshold,
        "classifier_fitted": equivalence_classifier.is_fitted,
        "calibrator_fitted": probability_calibrator.is_fitted,
        "vectors_loaded": faiss_service.total_vectors()
    }

def generate_synthetic_pairs_from_text(text: str, policy_id: str, domain: str = "HR") -> List[Dict[str, Any]]:
    """
    Generates candidate question pairs (positive paraphrases, numerical hard negatives,
    jurisdiction negatives, category negatives) from a policy text excerpt for admin review.
    """
    import re
    sentences = [s.strip() for s in re.split(r'[.\n]', text) if len(s.strip()) > 25]
    candidates = []

    for sentence in sentences[:6]:
        # Positive question paraphrase pair
        q1 = f"What is the company policy regarding {sentence[:60]}?"
        q2 = f"Could you explain the rule concerning {sentence[:60]}?"
        candidates.append({
            "q1": q1,
            "q2": q2,
            "label": 1,
            "group": f"{policy_id.lower()}_paraphrase",
            "pair_type": "positive"
        })

        # Numerical hard negative if numbers found
        nums = re.findall(r'\b\d+\b', sentence)
        if nums:
            num = int(nums[0])
            wrong_num = num * 2
            candidates.append({
                "q1": f"Is the limit {num} as specified in {policy_id}?",
                "q2": f"Is the limit {wrong_num} as specified in {policy_id}?",
                "label": 0,
                "group": f"{policy_id.lower()}_num_neg",
                "pair_type": "negative_numeric"
            })

        # Jurisdiction hard negative
        candidates.append({
            "q1": f"What is the entitlement in India under {policy_id}?",
            "q2": f"What is the entitlement in the United States under {policy_id}?",
            "label": 0,
            "group": f"{policy_id.lower()}_jurisdiction_neg",
            "pair_type": "negative_jurisdiction"
        })

        # Category hard negative
        candidates.append({
            "q1": f"Do full-time employees qualify under {policy_id}?",
            "q2": f"Do external contract workers qualify under {policy_id}?",
            "label": 0,
            "group": f"{policy_id.lower()}_category_neg",
            "pair_type": "negative_category"
        })

    return candidates

if __name__ == "__main__":
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        res = train_and_evaluate_all_models(db)
        print("Model training & evaluation pipeline completed successfully!")
        print(f"Selected Threshold: {res['threshold_evaluation']['selected_threshold']}")
    finally:
        db.close()
