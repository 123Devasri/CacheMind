import json
import csv
from pathlib import Path
from sqlalchemy.orm import Session

import os
from app.core.config import settings
from app.db.session import engine, Base
from app.models.entities import Policy, PolicyVersion, CachedEntry, DatasetRecord, ModelMetadata, User, Conversation
from app.core.security import hash_password

from app.ml.embeddings import embedding_service
from app.ml.faiss_index import faiss_service
from app.ml.policy_validation import normalize_text, extract_policy_conditions

# Real policies for Kaveri Tech Solutions Pvt. Ltd. (Headquarters: OMR, Chennai; Tech Branch: Tidel Park, Coimbatore, Tamil Nadu, India)
REAL_TAMIL_NADU_POLICIES = [
    {
        "policy_id": "TN-HR-LEAVE-01",
        "name": "Tamil Nadu Shops & Commercial Establishments Act Leave & Holiday Policy",
        "domain": "HR",
        "jurisdiction": "INDIA",
        "employee_category": "ALL",
        "current_version": "1.0",
        "content": (
            "Under the Tamil Nadu Shops and Establishments Act, full-time permanent employees of Kaveri Tech Solutions "
            "receive 18 days of Privilege/Annual Leave (PL), 12 days of Casual Leave (CL), and 12 days of Sick Leave (SL) per calendar year. "
            "Medical certificates from a registered practitioner are mandatory for sick leave exceeding 2 consecutive days. "
            "The company observes 10 mandatory Tamil Nadu state and national holidays annually, including Pongal (Thai Pongal, Thiruvalluvar Day, Uzhavar Thirunal), "
            "Tamil New Year, May Day, Independence Day, Gandhi Jayanthi, Ayudha Pooja, and Deepavali. "
            "Eligible female employees receive 26 weeks of fully paid Maternity Leave. "
            "Independent contractors and third-party vendor personnel are governed by their respective vendor contracts and do not accrue corporate paid leave."
        )
    },
    {
        "policy_id": "TN-HR-WFH-02",
        "name": "Chennai OMR & Coimbatore Hybrid Work and Remote Work Policy",
        "domain": "HR",
        "jurisdiction": "INDIA",
        "employee_category": "FULL_TIME",
        "current_version": "1.0",
        "content": (
            "Full-time engineering and operations employees based at Chennai OMR headquarters and Coimbatore Tidel Park "
            "are eligible for up to 2 days of Work-From-Home (WFH) per week, subject to engineering lead approval. "
            "Core business collaboration hours are 9:30 AM to 6:30 PM IST, Monday through Friday (5-day working week). "
            "Permanent employees working in hybrid mode can claim monthly broadband internet reimbursement up to INR 1,500 against valid GST invoices."
        )
    },
    {
        "policy_id": "TN-FIN-TRAVEL-03",
        "name": "Tamil Nadu Regional & India Domestic Business Travel Policy",
        "domain": "FINANCE",
        "jurisdiction": "INDIA",
        "employee_category": "ALL",
        "current_version": "1.0",
        "content": (
            "Domestic travel per diem meal allowance is INR 3,500 per day for Tier-1 metro destinations (Chennai, Bengaluru, Mumbai, Delhi) "
            "and INR 2,500 per day for Tier-2 cities (Coimbatore, Madurai, Trichy, Salem). "
            "Hotel accommodation expenses are capped at INR 6,500 per night for Tier-1 cities and INR 4,500 per night for Tier-2 cities. "
            "Local taxi, auto, and app-based ride hailing (Uber/Ola) expenses in Chennai and Coimbatore are reimbursable up to INR 1,200 per day against GST bills. "
            "Travel within Tamil Nadu is eligible for Vande Bharat Express or 2nd AC train travel, and inter-state flights over 4 hours qualify for economy air travel."
        )
    },
    {
        "policy_id": "TN-IT-SEC-04",
        "name": "IT Asset Management, Information Security & Remote Access Policy",
        "domain": "IT",
        "jurisdiction": "INDIA",
        "employee_category": "ALL",
        "current_version": "1.0",
        "content": (
            "All company-provisioned laptops (Lenovo ThinkPad / Apple MacBook Pro) must maintain full-disk BitLocker or FileVault encryption "
            "and active endpoint security agents. Accessing Kaveri Tech internal repositories, GitLab, and production systems outside "
            "Chennai OMR or Coimbatore office local networks strictly requires GlobalProtect VPN and Okta Multi-Factor Authentication (MFA). "
            "Data handling practices must strictly comply with the Indian Information Technology Act and the Digital Personal Data Protection (DPDP) Act 2023."
        )
    },
    {
        "policy_id": "TN-HR-HEALTH-05",
        "name": "Group Mediclaim Insurance & Employee Wellness Policy",
        "domain": "HR",
        "jurisdiction": "INDIA",
        "employee_category": "FULL_TIME",
        "current_version": "1.0",
        "content": (
            "Full-time permanent staff are covered under a Group Health Insurance (GMC) floater policy with a sum insured of INR 5,00,000 "
            "covering the employee, spouse, and up to 2 dependent children. Cashless hospitalization is supported across major network hospitals "
            "in Tamil Nadu including Apollo Hospitals Chennai, MIOT International, Kauvery Hospital Chennai, KG Hospital Coimbatore, and Ganga Hospital. "
            "Employees are also entitled to an annual comprehensive health checkup at partnered diagnostic clinics in Chennai and Coimbatore at zero out-of-pocket cost."
        )
    },
    {
        "policy_id": "TN-FIN-RELOC-06",
        "name": "Tamil Nadu Relocation & Transit Assistance Policy",
        "domain": "FINANCE",
        "jurisdiction": "INDIA",
        "employee_category": "FULL_TIME",
        "current_version": "1.0",
        "content": (
            "New hires relocating to the Chennai OMR campus or Coimbatore tech center from other districts or states receive a one-time relocation grant "
            "of INR 35,000 to assist with transition expenses. The company provides up to 14 consecutive days of corporate guest house stay in Chennai or Coimbatore. "
            "Professional household goods movement and packers expenses are reimbursable up to INR 25,000 upon presenting valid GST tax invoices."
        )
    },
    {
        "policy_id": "TN-HR-MEAL-07",
        "name": "Chennai OMR & Coimbatore Campus Cafeteria, Subsidized Meals & Digital Food Voucher Policy",
        "domain": "HR",
        "jurisdiction": "INDIA",
        "employee_category": "ALL",
        "current_version": "1.0",
        "content": (
            "Kaveri Tech Solutions provides subsidized multi-cuisine cafeteria facilities at the Chennai OMR (Navalur Campus) "
            "and Coimbatore Tidel Park offices. Wholesome breakfast, South/North Indian executive lunch thali, snacks, and beverages "
            "are served at subsidized rates of INR 40 per meal, with the remaining 60% subsidized by the company. "
            "All permanent full-time employees receive a monthly digital meal allowance / food voucher card (Pluxee / Sodexo) of INR 2,200, "
            "which is 100% tax-exempt under Section 17(2) of the Indian Income Tax Act. "
            "Employees working on client deliverables or second shifts past 8:30 PM IST receive complimentary dinner at the campus cafeteria "
            "along with pre-scheduled corporate cab drop facilities across Chennai and Coimbatore. "
            "Pantry stations on all office floors offer complimentary tea, South Indian filter coffee, and purified drinking water."
        )
    }
]

# Verified question-answer pairs for the semantic cache
REAL_CACHE_ENTRIES = [
    {
        "question": "How many days of annual leave do permanent employees get in Tamil Nadu?",
        "answer": "Under policy TN-HR-LEAVE-01 (Tamil Nadu Shops and Establishments Act), full-time permanent employees receive 18 days of Privilege/Annual Leave, 12 days of Casual Leave, and 12 days of Sick Leave per calendar year.",
        "policy_id": "TN-HR-LEAVE-01",
        "domain": "HR",
        "jurisdiction": "INDIA",
        "employee_category": "FULL_TIME",
        "numerical_limits": {"days": 18.0}
    },
    {
        "question": "Are contractors eligible for paid leave days in Chennai?",
        "answer": "No. Under policy TN-HR-LEAVE-01, independent contractors and vendor personnel are governed by their respective vendor contracts and do not receive corporate paid leave from Kaveri Tech Solutions.",
        "policy_id": "TN-HR-LEAVE-01",
        "domain": "HR",
        "jurisdiction": "INDIA",
        "employee_category": "CONTRACTOR",
        "numerical_limits": {"days": 0.0}
    },
    {
        "question": "How many days per week can employees work from home in Chennai and Coimbatore?",
        "answer": "Full-time employees may work remotely up to 2 days per week with engineering lead approval, as per policy TN-HR-WFH-02. Core hours are 9:30 AM to 6:30 PM IST.",
        "policy_id": "TN-HR-WFH-02",
        "domain": "HR",
        "jurisdiction": "INDIA",
        "employee_category": "FULL_TIME",
        "numerical_limits": {"days": 2.0}
    },
    {
        "question": "What is the monthly broadband internet reimbursement for remote work?",
        "answer": "Under policy TN-HR-WFH-02, permanent hybrid employees can claim up to INR 1,500 per month for high-speed broadband internet against valid GST invoices.",
        "policy_id": "TN-HR-WFH-02",
        "domain": "HR",
        "jurisdiction": "INDIA",
        "employee_category": "FULL_TIME",
        "numerical_limits": {"inr": 1500.0}
    },
    {
        "question": "What is the daily travel per diem allowance for business trips in India?",
        "answer": "Under policy TN-FIN-TRAVEL-03, domestic per diem is INR 3,500 per day for Tier-1 metros (Chennai, Bengaluru, Mumbai, Delhi) and INR 2,500 per day for Tier-2 cities (Coimbatore, Madurai, Trichy, Salem).",
        "policy_id": "TN-FIN-TRAVEL-03",
        "domain": "FINANCE",
        "jurisdiction": "INDIA",
        "employee_category": "ALL",
        "numerical_limits": {"inr": 3500.0}
    },
    {
        "question": "What is the per diem rate for travel to Coimbatore or Madurai?",
        "answer": "Under policy TN-FIN-TRAVEL-03, travel to Tier-2 cities such as Coimbatore, Madurai, Trichy, and Salem qualifies for a per diem allowance of INR 2,500 per day.",
        "policy_id": "TN-FIN-TRAVEL-03",
        "domain": "FINANCE",
        "jurisdiction": "INDIA",
        "employee_category": "ALL",
        "numerical_limits": {"inr": 2500.0}
    },
    {
        "question": "Is VPN mandatory when accessing company systems remotely?",
        "answer": "Yes. Policy TN-IT-SEC-04 strictly requires GlobalProtect VPN and Okta Multi-Factor Authentication (MFA) whenever accessing internal repositories and services outside Chennai OMR or Coimbatore offices.",
        "policy_id": "TN-IT-SEC-04",
        "domain": "IT",
        "jurisdiction": "INDIA",
        "employee_category": "ALL",
        "numerical_limits": {}
    },
    {
        "question": "What is the health insurance coverage limit for employees in Tamil Nadu?",
        "answer": "Under policy TN-HR-HEALTH-05, full-time employees receive Group Health Insurance coverage of INR 5,00,000 (floater) covering employee, spouse, and up to 2 children, with cashless network at Apollo, MIOT, and Kauvery hospitals.",
        "policy_id": "TN-HR-HEALTH-05",
        "domain": "HR",
        "jurisdiction": "INDIA",
        "employee_category": "FULL_TIME",
        "numerical_limits": {"inr": 500000.0}
    },
    {
        "question": "How much relocation allowance is provided for moving to Chennai or Coimbatore?",
        "answer": "Under policy TN-FIN-RELOC-06, new hires relocating to the Chennai OMR campus or Coimbatore office receive a one-time grant of INR 35,000 plus 14 days of corporate guest house accommodation.",
        "policy_id": "TN-FIN-RELOC-06",
        "domain": "FINANCE",
        "jurisdiction": "INDIA",
        "employee_category": "FULL_TIME",
        "numerical_limits": {"inr": 35000.0}
    },
    {
        "question": "What is the policy regarding employee cafeteria meals and food allowances?",
        "answer": "Under policy TN-HR-MEAL-07, Kaveri Tech Solutions provides subsidized multi-cuisine cafeteria dining (INR 40 per meal) at Chennai OMR and Coimbatore Tidel Park campuses. Full-time employees receive a monthly tax-exempt digital meal allowance of INR 2,200 (Pluxee/Sodexo). Complimentary dinner and cab drop are provided for employees working past 8:30 PM IST.",
        "policy_id": "TN-HR-MEAL-07",
        "domain": "HR",
        "jurisdiction": "INDIA",
        "employee_category": "ALL",
        "numerical_limits": {"inr": 2200.0}
    },
    {
        "question": "What is the monthly meal voucher or food allowance for employees?",
        "answer": "Under policy TN-HR-MEAL-07, full-time employees receive a monthly tax-exempt digital meal card allowance of INR 2,200 (Pluxee/Sodexo) under Section 17(2) of the Indian Income Tax Act.",
        "policy_id": "TN-HR-MEAL-07",
        "domain": "HR",
        "jurisdiction": "INDIA",
        "employee_category": "FULL_TIME",
        "numerical_limits": {"inr": 2200.0}
    },
    {
        "question": "Are cafeteria meals subsidized in Chennai and Coimbatore offices?",
        "answer": "Yes. Under policy TN-HR-MEAL-07, cafeteria meals including breakfast and executive lunch thalis are subsidized at INR 40 per meal across Chennai OMR and Coimbatore Tidel Park campuses, with 60% subsidized by Kaveri Tech Solutions.",
        "policy_id": "TN-HR-MEAL-07",
        "domain": "HR",
        "jurisdiction": "INDIA",
        "employee_category": "ALL",
        "numerical_limits": {"inr": 40.0}
    },
    {
        "question": "Do employees get free dinner when working late in Chennai or Coimbatore?",
        "answer": "Yes. Under policy TN-HR-MEAL-07, employees working past 8:30 PM IST receive complimentary dinner at the cafeteria along with scheduled corporate cab drop services.",
        "policy_id": "TN-HR-MEAL-07",
        "domain": "HR",
        "jurisdiction": "INDIA",
        "employee_category": "ALL",
        "numerical_limits": {}
    }
]

# Pair Dataset for Training, Calibration, Validation, and Test
REAL_QUESTION_PAIRS = [
    # --- Positive Paraphrase Pairs (High Semantic & Lexical Match) ---
    {"q1": "How many days of annual leave do permanent employees receive in Tamil Nadu?", "q2": "How many days of annual leave do permanent employees get in Tamil Nadu?", "label": 1, "group": "tn_leave_fte_direct"},
    {"q1": "What is the privilege leave entitlement for regular staff in Chennai?", "q2": "How many days of annual leave do permanent employees get in Tamil Nadu?", "label": 1, "group": "tn_leave_fte_direct"},
    {"q1": "How many vacation days do full-time staff get in Tamil Nadu?", "q2": "What is the annual leave allowance for permanent employees under TN policy?", "label": 1, "group": "tn_leave_fte"},
    {"q1": "Do contractors get paid time off in Chennai?", "q2": "Are contractors eligible for paid leave days in Chennai?", "label": 1, "group": "tn_contractor_leave"},
    {"q1": "Are temporary vendors eligible for company leave in Tamil Nadu?", "q2": "Are contractors eligible for paid leave days in Chennai?", "label": 1, "group": "tn_contractor_leave_direct"},
    {"q1": "How many days a week can staff work from home in Chennai?", "q2": "How many days per week can employees work from home in Chennai and Coimbatore?", "label": 1, "group": "tn_wfh_days"},
    {"q1": "Is remote work permitted 2 days a week for Coimbatore employees?", "q2": "How many days per week can employees work from home in Chennai and Coimbatore?", "label": 1, "group": "tn_wfh_days_direct"},
    {"q1": "What is the monthly internet allowance for WFH?", "q2": "What is the monthly broadband internet reimbursement for remote work?", "label": 1, "group": "tn_wifi_reimburse"},
    {"q1": "How much can I claim for home wifi bills?", "q2": "What is the monthly broadband internet reimbursement for remote work?", "label": 1, "group": "tn_wifi_reimburse_direct"},
    {"q1": "What is the daily per diem rate for travel in Chennai or Mumbai?", "q2": "What is the daily travel per diem allowance for business trips in India?", "label": 1, "group": "tn_travel_tier1"},
    {"q1": "What is the daily food allowance for business trips in Tier-1 cities?", "q2": "What is the daily travel per diem allowance for business trips in India?", "label": 1, "group": "tn_travel_tier1_direct"},
    {"q1": "What is the per diem allowance for Coimbatore and Madurai trips?", "q2": "What is the per diem rate for travel to Coimbatore or Madurai?", "label": 1, "group": "tn_travel_tier2"},
    {"q1": "How many rupees per day is the travel stipend in Trichy or Salem?", "q2": "What is the per diem rate for travel to Coimbatore or Madurai?", "label": 1, "group": "tn_travel_tier2_direct"},
    {"q1": "Is VPN required when working outside Chennai office?", "q2": "Is VPN mandatory when accessing company systems remotely?", "label": 1, "group": "tn_vpn_direct"},
    {"q1": "Do I have to connect to company VPN from home in Tamil Nadu?", "q2": "Is VPN mandatory when accessing company systems remotely?", "label": 1, "group": "tn_vpn_remote"},
    {"q1": "What is the medical insurance sum insured for employees?", "q2": "What is the health insurance coverage limit for employees in Tamil Nadu?", "label": 1, "group": "tn_mediclaim"},
    {"q1": "How much health cover is provided for family and kids?", "q2": "What is the health insurance coverage limit for employees in Tamil Nadu?", "label": 1, "group": "tn_mediclaim_direct"},
    {"q1": "How much relocation money is given for joining the Chennai office?", "q2": "How much relocation allowance is provided for moving to Chennai or Coimbatore?", "label": 1, "group": "tn_relocation"},
    {"q1": "What is the transit grant for new joiners relocating to Coimbatore?", "q2": "How much relocation allowance is provided for moving to Chennai or Coimbatore?", "label": 1, "group": "tn_relocation_direct"},
    {"q1": "What is the policy regarding employee cafeteria meals and food allowances?", "q2": "What is the policy regarding employee cafeteria meals and food allowances?", "label": 1, "group": "tn_cafeteria_meals_direct"},
    {"q1": "What are the food allowances and cafeteria rules in Chennai?", "q2": "What is the policy regarding employee cafeteria meals and food allowances?", "label": 1, "group": "tn_cafeteria_meals_direct"},
    {"q1": "What is the monthly food allowance or meal voucher for employees?", "q2": "What is the monthly meal voucher or food allowance for employees?", "label": 1, "group": "tn_food_allowance"},
    {"q1": "How much Sodexo or Pluxee food voucher is given per month?", "q2": "What is the monthly meal voucher or food allowance for employees?", "label": 1, "group": "tn_food_allowance_direct"},
    {"q1": "How much do cafeteria meals cost in Chennai OMR?", "q2": "Are cafeteria meals subsidized in Chennai and Coimbatore offices?", "label": 1, "group": "tn_cafeteria_subsidized"},
    {"q1": "Is dinner free if I work late past 8:30 PM?", "q2": "Do employees get free dinner when working late in Chennai or Coimbatore?", "label": 1, "group": "tn_late_dinner"},

    # --- Exact Match Pairs (Strong Grounding) ---
    {"q1": "How many days of annual leave do permanent employees get in Tamil Nadu?", "q2": "How many days of annual leave do permanent employees get in Tamil Nadu?", "label": 1, "group": "exact_leave"},
    {"q1": "Are contractors eligible for paid leave days in Chennai?", "q2": "Are contractors eligible for paid leave days in Chennai?", "label": 1, "group": "exact_contractor"},
    {"q1": "How many days per week can employees work from home in Chennai and Coimbatore?", "q2": "How many days per week can employees work from home in Chennai and Coimbatore?", "label": 1, "group": "exact_wfh"},
    {"q1": "What is the monthly broadband internet reimbursement for remote work?", "q2": "What is the monthly broadband internet reimbursement for remote work?", "label": 1, "group": "exact_wifi"},
    {"q1": "What is the daily travel per diem allowance for business trips in India?", "q2": "What is the daily travel per diem allowance for business trips in India?", "label": 1, "group": "exact_travel"},
    {"q1": "Is VPN mandatory when accessing company systems remotely?", "q2": "Is VPN mandatory when accessing company systems remotely?", "label": 1, "group": "exact_vpn"},
    {"q1": "What is the health insurance coverage limit for employees in Tamil Nadu?", "q2": "What is the health insurance coverage limit for employees in Tamil Nadu?", "label": 1, "group": "exact_mediclaim"},
    {"q1": "What is the policy regarding employee cafeteria meals and food allowances?", "q2": "What is the policy regarding employee cafeteria meals and food allowances?", "label": 1, "group": "exact_cafeteria"},

    # --- Negatives (Adversarial Mismatches & Numerical / Jurisdiction Flips) ---
    {"q1": "How many days of annual leave do permanent employees get in Tamil Nadu?", "q2": "Are contractors eligible for paid leave days in Chennai?", "label": 0, "group": "adv_cat_mismatch"},
    {"q1": "Can permanent staff work remotely 2 days a week in Chennai?", "q2": "Can permanent staff work remotely 5 days a week in Chennai?", "label": 0, "group": "adv_numeric_wfh"},
    {"q1": "Is the Tier-1 per diem INR 3,500 per day?", "q2": "Is the Tier-1 per diem INR 5,000 per day?", "label": 0, "group": "adv_numeric_travel"},
    {"q1": "Is the travel allowance for Coimbatore INR 2,500?", "q2": "Is the travel allowance for Coimbatore INR 3,500?", "label": 0, "group": "adv_numeric_tier2"},
    {"q1": "What is the travel per diem in Chennai India?", "q2": "What is the travel per diem in New York USA?", "label": 0, "group": "adv_jurisdiction_flip"},
    {"q1": "Is health insurance coverage INR 5,00,000 for permanent staff?", "q2": "Is health insurance coverage INR 15,00,000 for permanent staff?", "label": 0, "group": "adv_numeric_insurance"},
    {"q1": "Is VPN mandatory when working remotely in Chennai?", "q2": "Is VPN optional when working remotely in Chennai?", "label": 0, "group": "adv_negation_vpn"},
    {"q1": "Do contractors get company health insurance in Tamil Nadu?", "q2": "Do full-time employees get company health insurance in Tamil Nadu?", "label": 0, "group": "adv_category_insurance"},
    {"q1": "What is the monthly wifi reimbursement in Chennai?", "q2": "What is the daily travel per diem allowance in India?", "label": 0, "group": "adv_cross_domain_wfh_travel"},
    {"q1": "How many days of annual leave do employees receive?", "q2": "Must company laptops have full disk encryption?", "label": 0, "group": "adv_cross_domain_hr_it"},
    {"q1": "Is the monthly meal voucher INR 2,200?", "q2": "Is the monthly meal voucher INR 5,000?", "label": 0, "group": "adv_numeric_meal"},
    {"q1": "Is dinner complimentary after 8:30 PM IST?", "q2": "Is dinner complimentary during normal daytime hours?", "label": 0, "group": "adv_timing_dinner"},

    # --- Cross-Domain Negatives ---
    {"q1": "How many days of annual leave do permanent employees get in Tamil Nadu?", "q2": "What is the monthly broadband internet reimbursement for remote work?", "label": 0, "group": "cross_leave_wifi"},
    {"q1": "How many days of annual leave do permanent employees get in Tamil Nadu?", "q2": "What is the daily travel per diem allowance for business trips in India?", "label": 0, "group": "cross_leave_travel"},
    {"q1": "How many days of annual leave do permanent employees get in Tamil Nadu?", "q2": "Is VPN mandatory when accessing company systems remotely?", "label": 0, "group": "cross_leave_vpn"},
    {"q1": "How many days of annual leave do permanent employees get in Tamil Nadu?", "q2": "What is the policy regarding employee cafeteria meals and food allowances?", "label": 0, "group": "cross_leave_cafeteria"},
    {"q1": "What is the monthly broadband internet reimbursement for remote work?", "q2": "What is the health insurance coverage limit for employees in Tamil Nadu?", "label": 0, "group": "cross_wifi_health"},
    {"q1": "What is the daily travel per diem allowance for business trips in India?", "q2": "Is VPN mandatory when accessing company systems remotely?", "label": 0, "group": "cross_travel_vpn"},
    {"q1": "Is VPN mandatory when accessing company systems remotely?", "q2": "What is the policy regarding employee cafeteria meals and food allowances?", "label": 0, "group": "cross_vpn_cafeteria"},
    {"q1": "What is the health insurance coverage limit for employees in Tamil Nadu?", "q2": "How much relocation allowance is provided for moving to Chennai or Coimbatore?", "label": 0, "group": "cross_health_reloc"}
]

def seed_database_and_datasets(db: Session):
    """
    Seeds database tables and saves CSV datasets with clean non-leaking group splits
    customized specifically for Tamil Nadu enterprise context.
    """
    print("Creating tables if not exists...")
    Base.metadata.create_all(bind=engine)

    # 0. Seed Users (Admin & Standard User)
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        admin_user = User(
            username="admin",
            email="admin@cachemind.internal",
            hashed_password=hash_password(os.environ.get("ADMIN_PASSWORD", "Admin@123")),
            role="ADMIN",
            full_name="System Administrator",
            department="IT & Governance",
            is_active=True
        )
        db.add(admin_user)
        db.commit()

    standard_user = db.query(User).filter(User.username == "user").first()
    if not standard_user:
        standard_user = User(
            username="user",
            email="user@cachemind.internal",
            hashed_password=hash_password("User@123"),
            role="USER",
            full_name="Enterprise Employee",
            department="Engineering",
            is_active=True
        )
        db.add(standard_user)
        db.commit()

        conv = Conversation(
            user_id=standard_user.id,
            title="General Policy Inquiries"
        )
        db.add(conv)
        db.commit()

    # 1. Clean previous generic policies if any, or seed Real Tamil Nadu Policies

    for p_data in REAL_TAMIL_NADU_POLICIES:
        pol = db.query(Policy).filter(Policy.policy_id == p_data["policy_id"]).first()
        if not pol:
            pol = Policy(**p_data)
            db.add(pol)
            db.commit()
            
            p_ver = PolicyVersion(
                policy_id=pol.policy_id,
                version="1.0",
                change_summary="Tamil Nadu enterprise policy baseline document.",
                content=pol.content,
                is_active=True
            )
            db.add(p_ver)
            db.commit()
        else:
            # Update existing to real Tamil Nadu content
            pol.name = p_data["name"]
            pol.content = p_data["content"]
            pol.domain = p_data["domain"]
            pol.jurisdiction = p_data["jurisdiction"]
            pol.employee_category = p_data["employee_category"]
            db.commit()

    # 2. Seed Cached Entries
    embeddings_to_add = []
    entry_ids = []

    for c_data in REAL_CACHE_ENTRIES:
        norm_q = normalize_text(c_data["question"])
        existing = db.query(CachedEntry).filter(CachedEntry.question == c_data["question"]).first()
        if not existing:
            entry = CachedEntry(
                question=c_data["question"],
                normalized_question=norm_q,
                answer=c_data["answer"],
                policy_id=c_data["policy_id"],
                policy_version="1.0",
                domain=c_data["domain"],
                jurisdiction=c_data["jurisdiction"],
                employee_category=c_data["employee_category"],
                numerical_limits=c_data["numerical_limits"],
                is_verified=True,
                is_active=True,
                hit_count=3
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            entry_ids.append(entry.id)
            embeddings_to_add.append(norm_q)
        else:
            existing.answer = c_data["answer"]
            existing.domain = c_data["domain"]
            existing.jurisdiction = c_data["jurisdiction"]
            existing.employee_category = c_data["employee_category"]
            existing.numerical_limits = c_data["numerical_limits"]
            db.commit()
            entry_ids.append(existing.id)
            embeddings_to_add.append(norm_q)

    # 3. Build & Populate FAISS index
    if embeddings_to_add:
        # First reset all faiss_ids to None to avoid unique constraint collisions during re-indexing
        db.query(CachedEntry).update({CachedEntry.faiss_id: None})
        db.commit()

        vectors = embedding_service.encode(embeddings_to_add, normalize=True)
        count = faiss_service.rebuild_index(entry_ids, vectors)
        print(f"FAISS index built with {count} verified vectors.")
        
        # Link faiss_id in database
        for idx, eid in enumerate(entry_ids):
            e_obj = db.query(CachedEntry).filter(CachedEntry.id == eid).first()
            if e_obj:
                e_obj.faiss_id = idx
        db.commit()

    # 4. Save CSV Datasets for Training / Calibration
    settings.DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    all_pairs_path = settings.DATASETS_DIR / "enterprise_policy_pairs.csv"
    split_pairs_path = settings.DATASETS_DIR / "enterprise_policy_pairs_split.csv"

    CALIBRATION_GROUPS = {
        "exact_wifi",
        "exact_leave",
        "tn_travel_tier1_direct",
        "adv_numeric_travel",
        "adv_jurisdiction_flip",
        "cross_leave_travel"
    }
    VALIDATION_GROUPS = {
        "exact_cafeteria",
        "tn_wfh_days_direct",
        "adv_numeric_wfh",
        "cross_wifi_travel"
    }
    TEST_GROUPS = {
        "exact_travel",
        "tn_mediclaim_direct",
        "adv_category_insurance",
        "cross_leave_vpn"
    }

    rows_with_split = []
    for row in REAL_QUESTION_PAIRS:
        grp = row.get("group", "")
        if grp in CALIBRATION_GROUPS:
            sp = "calibration"
        elif grp in VALIDATION_GROUPS:
            sp = "validation"
        elif grp in TEST_GROUPS:
            sp = "test"
        else:
            sp = "train"

        row_copy = dict(row)
        row_copy["split"] = sp
        rows_with_split.append(row_copy)

    with open(all_pairs_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["q1", "q2", "label", "group"])
        writer.writeheader()
        for row in REAL_QUESTION_PAIRS:
            writer.writerow(row)

    with open(split_pairs_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["q1", "q2", "label", "group", "split"])
        writer.writeheader()
        for row in rows_with_split:
            writer.writerow(row)

    print(f"Saved {len(REAL_QUESTION_PAIRS)} pairs to {all_pairs_path} and {split_pairs_path}")
    return len(REAL_TAMIL_NADU_POLICIES), len(REAL_CACHE_ENTRIES)

if __name__ == "__main__":
    from app.db.session import SessionLocal
    db = SessionLocal()
    p_cnt, c_cnt = seed_database_and_datasets(db)
    print(f"Seeding complete! Policies: {p_cnt}, Cached Entries: {c_cnt}")
