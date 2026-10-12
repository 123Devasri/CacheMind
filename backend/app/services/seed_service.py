import json
import csv
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import engine, Base
from app.models.entities import Policy, PolicyVersion, CachedEntry, DatasetRecord, ModelMetadata
from app.ml.embeddings import embedding_service
from app.ml.faiss_index import faiss_service
from app.ml.policy_validation import normalize_text, extract_policy_conditions

SYNTHETIC_POLICIES = [
    {
        "policy_id": "HR-LEAVE-01",
        "name": "Annual and Sick Leave Policy",
        "domain": "HR",
        "jurisdiction": "GLOBAL",
        "employee_category": "ALL",
        "current_version": "1.0",
        "content": "Full-time permanent employees receive 20 paid leave days annually. Contractors and temporary workers do not receive company paid leave. Unused leave expires at year end."
    },
    {
        "policy_id": "HR-WFH-02",
        "name": "Work From Home and Remote Work Policy",
        "domain": "HR",
        "jurisdiction": "GLOBAL",
        "employee_category": "FULL_TIME",
        "current_version": "1.0",
        "content": "Full-time staff are eligible for up to 2 days of remote work per week with manager approval. Contractors must follow their specific contract agreement."
    },
    {
        "policy_id": "FIN-TRAVEL-US-03",
        "name": "US Travel and Meal Per Diem Policy",
        "domain": "FINANCE",
        "jurisdiction": "US",
        "employee_category": "ALL",
        "current_version": "1.0",
        "content": "US business travel meal allowance is $75 per day. Itemized receipts are required for all expenses exceeding $25."
    },
    {
        "policy_id": "FIN-TRAVEL-IN-04",
        "name": "India Travel and Per Diem Policy",
        "domain": "FINANCE",
        "jurisdiction": "INDIA",
        "employee_category": "ALL",
        "current_version": "1.0",
        "content": "India travel per diem is INR 3,000 per day for domestic travel. Lodging is directly billed or reimbursed up to INR 6,000 per night."
    },
    {
        "policy_id": "IT-SECURITY-05",
        "name": "IT Equipment and Remote Access Policy",
        "domain": "IT",
        "jurisdiction": "GLOBAL",
        "employee_category": "ALL",
        "current_version": "1.0",
        "content": "Corporate laptops must run full-disk encryption and MDM software. Corporate VPN connection is required to access internal services outside the office network."
    }
]

# High quality synthetic question-answer pairs for the cache
SEED_CACHE_ENTRIES = [
    {
        "question": "How many days of annual leave do permanent employees get?",
        "answer": "Full-time permanent employees receive 20 days of paid annual leave per calendar year under policy HR-LEAVE-01.",
        "policy_id": "HR-LEAVE-01",
        "domain": "HR",
        "jurisdiction": "GLOBAL",
        "employee_category": "FULL_TIME",
        "numerical_limits": {"days": 20.0}
    },
    {
        "question": "Are contractors entitled to paid vacation days?",
        "answer": "No. Under policy HR-LEAVE-01, independent contractors and vendors do not receive corporate paid vacation or leave days.",
        "policy_id": "HR-LEAVE-01",
        "domain": "HR",
        "jurisdiction": "GLOBAL",
        "employee_category": "CONTRACTOR",
        "numerical_limits": {"days": 0.0}
    },
    {
        "question": "How many days per week can employees work remotely?",
        "answer": "Full-time staff may work remotely up to 2 days per week with line manager approval (policy HR-WFH-02).",
        "policy_id": "HR-WFH-02",
        "domain": "HR",
        "jurisdiction": "GLOBAL",
        "employee_category": "FULL_TIME",
        "numerical_limits": {"days": 2.0}
    },
    {
        "question": "What is the daily meal allowance for travel in the US?",
        "answer": "The US business travel meal per diem allowance is $75 per day as per policy FIN-TRAVEL-US-03.",
        "policy_id": "FIN-TRAVEL-US-03",
        "domain": "FINANCE",
        "jurisdiction": "US",
        "employee_category": "ALL",
        "numerical_limits": {"usd": 75.0}
    },
    {
        "question": "What is the domestic travel allowance in India?",
        "answer": "Under policy FIN-TRAVEL-IN-04, domestic business travel per diem in India is INR 3,000 per day.",
        "policy_id": "FIN-TRAVEL-IN-04",
        "domain": "FINANCE",
        "jurisdiction": "INDIA",
        "employee_category": "ALL",
        "numerical_limits": {"inr": 3000.0}
    },
    {
        "question": "Is VPN mandatory when accessing internal enterprise systems remotely?",
        "answer": "Yes. Corporate VPN and Okta authentication are mandatory for all remote access as specified in IT-SECURITY-05.",
        "policy_id": "IT-SECURITY-05",
        "domain": "IT",
        "jurisdiction": "GLOBAL",
        "employee_category": "ALL",
        "numerical_limits": {}
    }
]

# Pair Dataset for Training, Calibration, Validation, and Test
SEED_QUESTION_PAIRS = [
    # --- Positive Paraphrase Pairs (High Semantic & Lexical Match) ---
    {"q1": "How many days of annual leave do permanent employees receive?", "q2": "How many days of annual leave do permanent employees get?", "label": 1, "group": "hr_leave_fte_direct"},
    {"q1": "How many annual vacation days do permanent employees receive?", "q2": "How many days of annual leave do permanent employees get?", "label": 1, "group": "hr_leave_fte_direct"},
    {"q1": "How many annual leave days do full-time employees get?", "q2": "What is the vacation entitlement for permanent staff?", "label": 1, "group": "hr_leave_fte"},
    {"q1": "How many days of paid time off do regular workers receive?", "q2": "What is the annual PTO limit for full-time employees?", "label": 1, "group": "hr_leave_fte"},
    {"q1": "Do contractors get paid time off?", "q2": "Are temporary workers and vendors entitled to paid leave?", "label": 1, "group": "hr_leave_contractor"},
    {"q1": "Are contractors entitled to paid vacation days?", "q2": "Do independent contractors receive paid vacation?", "label": 1, "group": "hr_leave_contractor_direct"},
    {"q1": "Can employees work from home two days a week?", "q2": "Is remote work permitted up to 2 days weekly?", "label": 1, "group": "hr_wfh_days"},
    {"q1": "How many days per week can employees work remotely?", "q2": "How many days a week can staff work from home?", "label": 1, "group": "hr_wfh_days_direct"},
    {"q1": "What is the daily meal allowance for travel in the US?", "q2": "What is the daily meal stipend for US travel?", "label": 1, "group": "fin_perdiem_us_direct"},
    {"q1": "What is the meal allowance for travel in America?", "q2": "What is the daily per diem for US business trips?", "label": 1, "group": "fin_perdiem_us"},
    {"q1": "How much can I claim for daily meals in the USA?", "q2": "What is the per diem meal rate in the US?", "label": 1, "group": "fin_perdiem_us"},
    {"q1": "What is the domestic travel allowance in India?", "q2": "What is the domestic travel per diem rate in India?", "label": 1, "group": "fin_perdiem_india_direct"},
    {"q1": "What is the daily allowance for travel in India?", "q2": "What is the per diem rate for Indian domestic trips?", "label": 1, "group": "fin_perdiem_india"},
    {"q1": "How many rupees is the per diem in India?", "q2": "What is the daily travel meal stipend in INR?", "label": 1, "group": "fin_perdiem_india"},
    {"q1": "Is VPN mandatory when accessing internal enterprise systems remotely?", "q2": "Is VPN required to access company systems from home?", "label": 1, "group": "it_vpn_direct"},
    {"q1": "Is VPN needed to work from home?", "q2": "Do I have to connect to company VPN for remote access?", "label": 1, "group": "it_vpn_remote"},
    {"q1": "Is disk encryption required on company laptops?", "q2": "Must corporate laptops have hard drive encryption enabled?", "label": 1, "group": "it_encryption"},
    {"q1": "Can I take 20 days vacation this year?", "q2": "Are 20 days of annual leave provided to employees?", "label": 1, "group": "hr_leave_fte_2"},
    {"q1": "Do interns qualify for company paid vacation?", "q2": "Can summer interns claim paid time off?", "label": 1, "group": "hr_intern_pto"},
    {"q1": "What is the sick leave policy for contractors?", "q2": "Do contractors receive sick pay from the firm?", "label": 1, "group": "hr_leave_contractor_2"},
    {"q1": "Can I expense $100 without a receipt?", "q2": "Are receipts required for 100 dollar expenses?", "label": 1, "group": "fin_receipt_req"},
    {"q1": "How much can I spend on food in New York on travel?", "q2": "What is the meal budget for US domestic travel?", "label": 1, "group": "fin_perdiem_us_2"},
    {"q1": "What is the daily food allowance in Bangalore?", "q2": "How much per diem is provided for business trips to India?", "label": 1, "group": "fin_perdiem_india_2"},
    {"q1": "Is Okta SSO required for cloud logins?", "q2": "Must users authenticate through Okta single sign-on?", "label": 1, "group": "it_sso_cloud"},
    {"q1": "What happens to leftover annual leave at year end?", "q2": "Do unused vacation days carry over into next year?", "label": 1, "group": "hr_leave_rollover"},

    # --- Negatives (Adversarial Mismatches & Near Matches) ---
    {"q1": "How many annual leave days do permanent employees receive?", "q2": "How many leave days do contractors get?", "label": 0, "group": "hr_mismatch_category"},
    {"q1": "Can permanent staff work remotely 2 days a week?", "q2": "Can permanent staff work remotely 5 days a week?", "label": 0, "group": "hr_mismatch_numeric"},
    {"q1": "Do full-time workers get 20 days off?", "q2": "Do full-time workers get 10 days off?", "label": 0, "group": "hr_mismatch_numeric"},
    {"q1": "Are contractors entitled to paid leave?", "q2": "Are contractors not entitled to paid leave?", "label": 0, "group": "hr_negation_flip"},
    {"q1": "What is the travel per diem in the US?", "q2": "What is the travel allowance in India?", "label": 0, "group": "fin_jurisdiction_conflict"},
    {"q1": "Is the US travel meal rate $75 a day?", "q2": "Is the US travel meal rate $150 a day?", "label": 0, "group": "fin_amount_conflict"},
    {"q1": "Do I need receipts for expenses over $25?", "q2": "Do I need receipts for expenses under $25?", "label": 0, "group": "fin_threshold_conflict"},
    {"q1": "Is India per diem INR 3000?", "q2": "Is India per diem INR 5000?", "label": 0, "group": "fin_amount_conflict"},
    {"q1": "Is VPN mandatory for office employees?", "q2": "Is VPN mandatory for remote workers?", "label": 0, "group": "it_scope_conflict"},
    {"q1": "Can I use my personal laptop for work?", "q2": "Can I use corporate laptops for work?", "label": 0, "group": "it_device_conflict"},
    {"q1": "Do contractors get company-issued laptops?", "q2": "Do permanent employees get company-issued laptops?", "label": 0, "group": "it_category_conflict"},
    {"q1": "How many annual leave days do permanent employees receive?", "q2": "What is the daily per diem for US business trips?", "label": 0, "group": "cross_domain_hr_fin"},
    {"q1": "Can employees work from home two days a week?", "q2": "Do I need receipts for travel expenses?", "label": 0, "group": "cross_domain_hr_fin_2"},
    {"q1": "What is the travel per diem in the US?", "q2": "Is corporate VPN mandatory for remote work?", "label": 0, "group": "cross_domain_fin_it"},
    {"q1": "How many days of paid time off do regular workers receive?", "q2": "Must enterprise laptops have full disk encryption?", "label": 0, "group": "cross_domain_hr_it"},
    {"q1": "What is the domestic travel allowance in India?", "q2": "How many days per week can staff work remotely?", "label": 0, "group": "cross_domain_fin_hr"},
    {"q1": "Is Okta SSO required for cloud logins?", "q2": "What is the daily travel meal stipend in INR?", "label": 0, "group": "cross_domain_it_fin"},
    {"q1": "Are contractors entitled to paid leave?", "q2": "What happens to leftover vacation at year end?", "label": 0, "group": "hr_diff_topics"},
    {"q1": "What is the domestic travel allowance in India?", "q2": "Do I need receipts for expenses over $25?", "label": 0, "group": "fin_diff_topics"},
    {"q1": "Is disk encryption optional on company MacBooks?", "q2": "Is disk encryption compulsory on enterprise laptops?", "label": 0, "group": "it_opt_compulsory"}
]

def seed_database_and_datasets(db: Session):
    """
    Seeds database tables and saves CSV datasets with clean non-leaking group splits.
    """
    print("Creating tables if not exists...")
    Base.metadata.create_all(bind=engine)

    # 1. Seed Policies
    for p_data in SYNTHETIC_POLICIES:
        pol = db.query(Policy).filter(Policy.policy_id == p_data["policy_id"]).first()
        if not pol:
            pol = Policy(**p_data)
            db.add(pol)
            db.commit()
            
            # Add version 1.0
            p_ver = PolicyVersion(
                policy_id=pol.policy_id,
                version="1.0",
                change_summary="Initial synthetic policy document.",
                content=pol.content,
                is_active=True
            )
            db.add(p_ver)
            db.commit()

    # 2. Seed Cached Entries
    embeddings_to_add = []
    entry_ids = []

    for entry_data in SEED_CACHE_ENTRIES:
        existing = db.query(CachedEntry).filter(CachedEntry.question == entry_data["question"]).first()
        if not existing:
            norm_q = normalize_text(entry_data["question"])
            cached_obj = CachedEntry(
                question=entry_data["question"],
                normalized_question=norm_q,
                answer=entry_data["answer"],
                policy_id=entry_data["policy_id"],
                domain=entry_data["domain"],
                jurisdiction=entry_data.get("jurisdiction", "GLOBAL"),
                employee_category=entry_data.get("employee_category", "ALL"),
                numerical_limits=entry_data.get("numerical_limits", {}),
                is_verified=True,
                is_active=True
            )
            db.add(cached_obj)
            db.commit()
            db.refresh(cached_obj)
            
            emb = embedding_service.encode(norm_q, normalize=True)
            cached_obj.faiss_id = faiss_service.add_vector(cached_obj.id, emb)
            db.commit()

    # 3. Create Dataset CSV with Group Splits using built-in csv module
    csv_path = settings.DATASETS_DIR / "enterprise_policy_pairs_seed.csv"
    fieldnames = ["q1", "q2", "label", "group"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(SEED_QUESTION_PAIRS)
    
    # Stratified group splitting: separate groups by majority label so all splits have both pos and neg
    pos_groups = []
    neg_groups = []
    for p in SEED_QUESTION_PAIRS:
        grp = p["group"]
        if p["label"] == 1:
            if grp not in pos_groups: pos_groups.append(grp)
        else:
            if grp not in neg_groups: neg_groups.append(grp)
            
    # Deterministically order groups so each split gets a realistic mixture of hard negatives and cross-domain negatives
    import random
    rng = random.Random(42)
    rng.shuffle(pos_groups)
    rng.shuffle(neg_groups)

    def split_group_list(grps):
        n = len(grps)
        t_end = max(1, int(0.55 * n))
        c_end = max(t_end + 1, int(0.75 * n))
        v_end = max(c_end + 1, int(0.88 * n))
        return set(grps[:t_end]), set(grps[t_end:c_end]), set(grps[c_end:v_end]), set(grps[v_end:])

    train_pos, cal_pos, val_pos, test_pos = split_group_list(pos_groups)
    train_neg, cal_neg, val_neg, test_neg = split_group_list(neg_groups)

    train_groups = train_pos | train_neg
    cal_groups = cal_pos | cal_neg
    val_groups = val_pos | val_neg
    test_groups = test_pos | test_neg
    
    split_rows = []
    split_counts = {"train": 0, "calibration": 0, "validation": 0, "test": 0}
    pos_count = 0
    neg_count = 0

    for p in SEED_QUESTION_PAIRS:
        grp = p["group"]
        if grp in cal_groups:
            s = "calibration"
        elif grp in val_groups:
            s = "validation"
        elif grp in test_groups:
            s = "test"
        else:
            s = "train"
        
        split_counts[s] += 1
        if p["label"] == 1:
            pos_count += 1
        else:
            neg_count += 1
            
        row_dict = dict(p)
        row_dict["split"] = s
        split_rows.append(row_dict)

    split_csv_path = settings.DATASETS_DIR / "enterprise_policy_pairs_split.csv"
    with open(split_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames + ["split"])
        writer.writeheader()
        writer.writerows(split_rows)

    # Save to DatasetRecord table
    d_rec = db.query(DatasetRecord).filter(DatasetRecord.name == "enterprise_policy_seed").first()
    if not d_rec:
        d_rec = DatasetRecord(
            name="enterprise_policy_seed",
            file_path=str(split_csv_path),
            row_count=len(split_rows),
            positive_count=pos_count,
            negative_count=neg_count,
            split_info=split_counts
        )
        db.add(d_rec)
        db.commit()

    print("Database seeding completed successfully.")

if __name__ == "__main__":
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        seed_database_and_datasets(db)
    finally:
        db.close()
