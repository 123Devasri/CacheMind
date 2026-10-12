# Governed Semantic Cache for Enterprise AI Assistants

A production-grade, end-to-end Machine Learning application providing an intelligent, policy-governed semantic cache for enterprise assistants (HR, IT, Finance). Designed to reduce redundant LLM inference costs and latency while strictly enforcing deterministic policy constraints and statistical safety bounds on False-Hit Rate (FHR).

---

## 1. System Architecture & ML Pipeline

```
Incoming Query
    │
    ▼
[1] Text Normalization & Cleaning
    │
    ▼
[2] Policy Scope & Condition Extraction (Regex & Pydantic)
    │  ├─ Domain (HR / IT / Finance)
    │  ├─ Jurisdiction (US / India / UK / Global)
    │  ├─ Employee Category (Full-Time / Contractor / Intern)
    │  └─ Numerical Limits & Negation Checks
    │
    ▼
[3] Sentence Transformer Embedding (all-MiniLM-L6-v2, 384-D, L2-Normalized)
    │
    ▼
[4] Dense FAISS Retrieval (IndexFlatIP Inner Product = Cosine Similarity)
    │  └─ Min Similarity Filter & Top-K Candidates
    │
    ▼
[5] Deterministic Policy-Safety Guard (Mandatory Check)
    │  ├─ Failed? ──► REJECT ──► LLM / Local Mock Fallback
    │  └─ Passed? ──► Proceed to Classification
    │
    ▼
[6] Feature Vector Generation (8 Handcrafted Domain Features)
    │
    ▼
[7] Logistic Regression Equivalence Classifier (StandardScaler + L2 Pipeline)
    │
    ▼
[8] Isotonic Regression Probability Calibration (Non-Parametric Posterior P(y=1|s))
    │
    ▼
[9] Statistical Acceptance Threshold (Clopper-Pearson Exact Binomial Upper Bound)
    │  ├─ Calibrated Probability >= Active Threshold? ──► CACHE HIT (Return Verified Answer)
    │  └─ Below Threshold? ───────────────────────────► CACHE MISS (Fallback Inference)
    │
    ▼
[10] Real-Time Query Audit Logging & Latency Tracking
```

*Note: Unsupervised **K-Means Clustering** with 2D PCA projection runs independently over stored query embeddings as an analytical monitor for recurring employee policy inquiries; it does not approve cache hits.*

---

## 2. Technology Stack

- **Machine Learning & NLP**:
  - `sentence-transformers` (`all-MiniLM-L6-v2`)
  - `faiss-cpu` (`IndexFlatIP`, Cosine Inner Product search)
  - `scikit-learn` (`LogisticRegression`, `IsotonicRegression`, `KMeans`, `StandardScaler`, `PCA`)
  - `scipy.stats` (Clopper-Pearson exact binomial confidence bounds)
  - `numpy` & `csv`

- **Backend**:
  - `FastAPI` (Async REST API, OpenAPI Docs)
  - `Pydantic v2` (Validation schemas & condition parsing)
  - `SQLAlchemy` (ORM persistence, SQLite default, PostgreSQL compatible)
  - `pytest` & `httpx` (Automated testing suite)

- **Frontend**:
  - `React 19` + `Vite` + `TypeScript`
  - `Tailwind CSS v4`
  - `Recharts` (Visualizing threshold bounds and query volumes)
  - `Lucide React` (Clean modern enterprise UI)
  - `React Router v7`

---

## 3. Quickstart & Local Setup Guide (Windows PowerShell)

### Prerequisites
- Python 3.10+ (Verified on Python 3.11.9)
- Node.js 18+ and npm (Verified on Node v24.16.0)

### Step 1: Clone & Configure Environment
```powershell
cd "ml_pro"
Copy-Item .env.example .env
```

### Step 2: Install Backend Dependencies
```powershell
cd backend
pip install -r requirements.txt
# Alternatively: pip install fastapi uvicorn pydantic pydantic-settings sqlalchemy sentence-transformers faiss-cpu scikit-learn scipy pytest httpx
```

### Step 3: Seed Synthetic Policies & Train ML Models
```powershell
# 1. Initialize DB and seed synthetic enterprise policies
python -m app.services.seed_service

# 2. Train Logistic Regression, fit Isotonic Calibrator, and evaluate threshold bounds
python -m app.services.training_service
```

### Step 4: Run Automated Backend Tests
Verify all 16 automated test suites (Deterministic safety, Clopper-Pearson bounds, and E2E APIs):
```powershell
python -m pytest -v
```

### Step 5: Start FastAPI Backend
```powershell
python app/main.py
# Backend API will be active at: http://127.0.0.1:8000
# OpenAPI Interactive Docs at: http://127.0.0.1:8000/docs
```

### Step 6: Start React Frontend
In a separate PowerShell terminal:
```powershell
cd ../frontend
npm install
npm run dev
# Frontend application will open at: http://localhost:5173
```

---

## 4. UI Dashboard Walkthrough

1. **Overview Dashboard** (`/`):
   - Real-time KPIs: Cache Hit Ratio, Average Lookup Latency (ms) vs Fallback Latency (ms), Inference Dollars Saved, and Observed False-Hit Rate (FHR).
   - Dynamic Bar Chart of cache hits vs fallback queries.
   - Live status indicators for all ML pipeline models.

2. **Interactive Query Playground** (`/playground`):
   - Real-time question testing with quick scenarios (Safe paraphrases vs adversarial condition mismatches).
   - Side-by-side diagnostic cards showing Cosine Similarity, Logistic Regression score, Isotonic calibrated probability, and deterministic safety checks.

3. **Cache Explorer** (`/cache`):
   - Searchable table of verified policy entries.
   - Direct button to trigger **FAISS Index Rebuild** with vector status counters.
   - Form to add new verified policy answers.

4. **ML Models Inspection** (`/models`):
   - Full technical specifications and weights for `all-MiniLM-L6-v2`, `IndexFlatIP`, `Logistic Regression`, and `Isotonic Regression`.

5. **Dataset & Training Pipeline** (`/training`):
   - Inspect group-stratified splits (Train 60%, Calibration 20%, Validation 10%, Test 10%) preventing topic leakage.
   - Action button to trigger model retraining asynchronously.

6. **Threshold Safety Evaluation** (`/thresholds`):
   - Interactive chart showing candidate thresholds &tau; against Observed FHR and Clopper-Pearson Upper Confidence Bounds.
   - Academic integrity notice indicating statistical sample size limitations.

7. **Query Clusters** (`/clusters`):
   - Unsupervised K-Means clustering with 2D PCA projection scatter plot and auto-extracted keyword tags.

8. **Audit Logs** (`/logs`):
   - Timestamped query trace logs with rejection reasons and one-click **Export to CSV**.

9. **Settings** (`/settings`):
   - Adjust minimum cosine similarity, top-K candidates, and configure fallback providers (Local Mock or OpenAI).

---

## 5. Statistical Safety & Academic Defense

### Why Clopper-Pearson?
Standard asymptotic normal approximations for confidence intervals fail when the event rate is near zero (e.g., target 1% False-Hit Rate). The **Clopper-Pearson** method calculates exact binomial confidence bounds using the Beta distribution:
$$\text{UCB} = \text{Beta.ppf}(1 - \alpha, k + 1, n - k)$$
Where $k$ is observed false hits, $n$ is total cache hits evaluated, and $\alpha$ is the significance level (0.05 for 95% confidence).

### Academic Integrity
When evaluating on small sample sizes ($N < 100$), Clopper-Pearson intervals are mathematically conservative. Rather than falsely claiming a 1.0% FHR, the system honestly reports the exact sample size, observed false hits, and Upper Confidence Bound, activating **conservative fallback mode** until sufficient labeled validation volume is collected.
