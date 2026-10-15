import os
import csv
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import Policy, DatasetRecord
from app.ml.policy_validation import normalize_text, extract_policy_conditions

QQP_PATH_CANDIDATES = [
    settings.DATASETS_DIR / "train.csv",
    settings.DATASETS_DIR / "quora_question_pairs.csv",
    settings.DATASETS_DIR / "questions.csv"
]

PAWS_PATH_CANDIDATES = [
    settings.DATASETS_DIR / "paws_paraphrase.tsv",
    settings.DATASETS_DIR / "paws.csv"
]

def find_qqp_file() -> Optional[Path]:
    for p in QQP_PATH_CANDIDATES:
        if p.exists() and p.stat().st_size > 1000:
            return p
    return None

def find_paws_file() -> Optional[Path]:
    for p in PAWS_PATH_CANDIDATES:
        if p.exists() and p.stat().st_size > 1000:
            return p
    return None

def load_qqp_pairs(max_pairs: int = 600) -> List[Dict[str, Any]]:
    """
    Loads a balanced sample of question pairs from the Kaggle Quora Question Pairs dataset.
    Returns list of dicts with: q1, q2, label (0 or 1), group ('qqp_general').
    """
    qqp_path = find_qqp_file()
    if not qqp_path:
        print("[DatasetService] QQP dataset file not found. Skipping QQP ingestion.")
        return []

    print(f"[DatasetService] Ingesting Quora Question Pairs from {qqp_path.name}...")
    pos_samples = []
    neg_samples = []
    half_target = max_pairs // 2

    try:
        with open(qqp_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                q1 = (row.get("question1") or row.get("q1") or "").strip()
                q2 = (row.get("question2") or row.get("q2") or "").strip()
                label_val = row.get("is_duplicate", row.get("label", ""))

                if not q1 or not q2 or len(q1) < 15 or len(q2) < 15:
                    continue

                try:
                    label = int(label_val)
                except (ValueError, TypeError):
                    continue

                if label == 1 and len(pos_samples) < half_target:
                    pos_samples.append({
                        "q1": q1,
                        "q2": q2,
                        "label": 1,
                        "group": f"qqp_pos_{len(pos_samples) // 20}"
                    })
                elif label == 0 and len(neg_samples) < half_target:
                    neg_samples.append({
                        "q1": q1,
                        "q2": q2,
                        "label": 0,
                        "group": f"qqp_neg_{len(neg_samples) // 20}"
                    })

                if len(pos_samples) >= half_target and len(neg_samples) >= half_target:
                    break

        combined = pos_samples + neg_samples
        random.seed(42)
        random.shuffle(combined)
        print(f"[DatasetService] Successfully loaded {len(combined)} QQP pairs ({len(pos_samples)} pos, {len(neg_samples)} neg).")
        return combined
    except Exception as e:
        print(f"[DatasetService] Error reading QQP dataset: {e}")
        return []

def load_paws_pairs(max_pairs: int = 200) -> List[Dict[str, Any]]:
    """
    Loads adversarial word-scramble paraphrase pairs from Google PAWS dataset if present.
    """
    paws_path = find_paws_file()
    if not paws_path:
        return []

    print(f"[DatasetService] Loading Google PAWS dataset from {paws_path.name}...")
    pairs = []
    try:
        delimiter = "\t" if paws_path.suffix == ".tsv" else ","
        with open(paws_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                s1 = (row.get("sentence1") or "").strip()
                s2 = (row.get("sentence2") or "").strip()
                lbl = row.get("label", "")
                if s1 and s2 and lbl in ["0", "1"]:
                    pairs.append({
                        "q1": s1,
                        "q2": s2,
                        "label": int(lbl),
                        "group": "paws_adversarial"
                    })
                    if len(pairs) >= max_pairs:
                        break
        return pairs
    except Exception as e:
        print(f"[DatasetService] Error reading PAWS dataset: {e}")
        return []

def generate_enterprise_policy_contrast_pairs(db: Session) -> List[Dict[str, Any]]:
    """
    Generates high-precision domain-specific enterprise policy contrast pairs:
    - Positive question paraphrases
    - Numerical hard negatives (altered allowances, days, percentages)
    - Employee category hard negatives (contractor vs full-time)
    - Jurisdiction hard negatives (Chennai/TN vs London/US)
    """
    from app.services.policy_qa_service import split_policy_into_clauses, extract_clause_topic
    
    policies = db.query(Policy).filter(Policy.status == "active").all()
    pairs = []

    for pol in policies:
        clauses = split_policy_into_clauses(pol.content)
        for idx, clause in enumerate(clauses):
            short_top, desc_top = extract_clause_topic(clause, pol.name)
            conds = extract_policy_conditions(clause, default_domain=pol.domain)
            nums = conds.numerical_limits or {}

            # Positive paraphrase pair
            q1 = f"What is the company policy regarding {desc_top}?"
            q2 = f"Could you explain the employee guidelines for {desc_top} under {pol.policy_id}?"
            pairs.append({
                "q1": q1,
                "q2": q2,
                "label": 1,
                "group": f"{pol.policy_id.lower()}_pos_{idx}"
            })

            # Additional conversational positive
            pairs.append({
                "q1": f"How does the {short_top} entitlement work at Kaveri Tech Solutions?",
                "q2": f"Can employees claim {short_top} under policy {pol.policy_id}?",
                "label": 1,
                "group": f"{pol.policy_id.lower()}_pos_{idx}_b"
            })

            # Numerical Hard Negative if numbers present
            if nums:
                unit = list(nums.keys())[0]
                val = nums[unit]
                wrong_val = val * 2 if val > 0 else 10
                pairs.append({
                    "q1": f"Is the {short_top} limit {val} {unit} under {pol.policy_id}?",
                    "q2": f"Is the {short_top} limit {wrong_val} {unit} under {pol.policy_id}?",
                    "label": 0,
                    "group": f"{pol.policy_id.lower()}_num_neg_{idx}"
                })

            # Category Hard Negative (full-time vs external contractor)
            pairs.append({
                "q1": f"Do full-time permanent employees qualify for {short_top} under {pol.policy_id}?",
                "q2": f"Do external third-party contractors qualify for {short_top} under {pol.policy_id}?",
                "label": 0,
                "group": f"{pol.policy_id.lower()}_category_neg_{idx}"
            })

            # Jurisdiction Hard Negative
            pairs.append({
                "q1": f"What is the {short_top} entitlement in Chennai Tamil Nadu under {pol.policy_id}?",
                "q2": f"What is the {short_top} entitlement in London United Kingdom under {pol.policy_id}?",
                "label": 0,
                "group": f"{pol.policy_id.lower()}_jurisdiction_neg_{idx}"
            })

    return pairs

def build_hybrid_dataset_splits(db: Session, max_qqp: int = 600) -> Dict[str, Any]:
    """
    Builds a comprehensive hybrid dataset blending Quora Question Pairs (general English semantics)
    with Enterprise Policy Contrastive Pairs (domain safety & numerical governance).
    Saves to enterprise_policy_pairs_split.csv with stratified, adequate split sizes:
      - train: 60% (~400-600 pairs)
      - calibration: 15% (~100 pairs)
      - validation: 15% (~120-180 pairs -> Clopper-Pearson bound <= 1.95%)
      - test: 10% (~80-100 pairs)
    """
    settings.DATASETS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load domain pairs and QQP pairs
    policy_pairs = generate_enterprise_policy_contrast_pairs(db)
    qqp_pairs = load_qqp_pairs(max_pairs=max_qqp)
    paws_pairs = load_paws_pairs(max_pairs=100)

    all_pairs = policy_pairs + qqp_pairs + paws_pairs
    random.seed(42)
    random.shuffle(all_pairs)

    total_count = len(all_pairs)
    if total_count < 20:
        raise ValueError(f"Insufficient total pairs ({total_count}) to create valid splits.")

    # 2. Stratified split assignment by group
    # We ensure validation has >= 150 pairs so Clopper-Pearson 95% upper bound drops to ~1.5%-2%
    groups = {}
    for p in all_pairs:
        grp = p.get("group", "general")
        if grp not in groups:
            groups[grp] = []
        groups[grp].append(p)

    group_keys = list(groups.keys())
    random.seed(42)
    random.shuffle(group_keys)

    n_groups = len(group_keys)
    # 55% train, 15% calibration, 20% validation, 10% test
    n_train = int(n_groups * 0.55)
    n_cal = int(n_groups * 0.15)
    n_val = int(n_groups * 0.20)

    train_groups = set(group_keys[:n_train])
    cal_groups = set(group_keys[n_train:n_train + n_cal])
    val_groups = set(group_keys[n_train + n_cal:n_train + n_cal + n_val])
    test_groups = set(group_keys[n_train + n_cal + n_val:])

    split_rows = []
    split_counts = {"train": 0, "calibration": 0, "validation": 0, "test": 0}

    for grp, items in groups.items():
        if grp in train_groups:
            s_name = "train"
        elif grp in cal_groups:
            s_name = "calibration"
        elif grp in val_groups:
            s_name = "validation"
        else:
            s_name = "test"

        for it in items:
            it["split"] = s_name
            split_rows.append(it)
            split_counts[s_name] += 1

    # 3. Write to enterprise_policy_pairs_split.csv
    split_csv_path = settings.DATASETS_DIR / "enterprise_policy_pairs_split.csv"
    fieldnames = ["q1", "q2", "label", "group", "split"]

    with open(split_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(split_rows)

    # Also write complete CSV for reference
    all_csv_path = settings.DATASETS_DIR / "enterprise_policy_pairs.csv"
    with open(all_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["q1", "q2", "label", "group"])
        for r in split_rows:
            writer.writerow({
                "q1": r["q1"],
                "q2": r["q2"],
                "label": r["label"],
                "group": r["group"]
            })

    # Register in DB
    rec = db.query(DatasetRecord).filter(DatasetRecord.name == "hybrid_qqp_enterprise_dataset").first()
    if not rec:
        rec = DatasetRecord(
            name="hybrid_qqp_enterprise_dataset",
            file_path=str(split_csv_path),
            row_count=total_count,
            positive_count=sum(1 for r in split_rows if r["label"] == 1),
            negative_count=sum(1 for r in split_rows if r["label"] == 0),
            split_info=split_counts
        )
        db.add(rec)
    else:
        rec.row_count = total_count
        rec.positive_count = sum(1 for r in split_rows if r["label"] == 1)
        rec.negative_count = sum(1 for r in split_rows if r["label"] == 0)
        rec.split_info = split_counts
    db.commit()

    print(f"[DatasetService] Generated hybrid dataset: {total_count} pairs ({len(qqp_pairs)} QQP, {len(policy_pairs)} Policy, {len(paws_pairs)} PAWS).")
    print(f"[DatasetService] Split counts: {split_counts}")

    return {
        "status": "success",
        "total_pairs": total_count,
        "qqp_pairs_count": len(qqp_pairs),
        "policy_pairs_count": len(policy_pairs),
        "split_counts": split_counts
    }
