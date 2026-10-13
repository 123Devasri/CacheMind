# CacheMind: Governed Semantic Cache for Enterprise AI Assistants

An enterprise-grade, end-to-end Machine Learning and AI governance system providing a policy-governed semantic cache for organizational assistants (HR, Finance, IT, Operations). Built to eliminate redundant generative inference costs, slash response latencies from seconds to single-digit milliseconds, and strictly enforce deterministic policy boundaries with exact statistical false-hit rate guarantees.

---

## 1. Fixed ML Model Stack (Strictly Implemented)

The core machine learning pipeline strictly adheres to established algorithms without custom LLM training or heavy third-party dependencies:

1. **Sentence Transformer (`sentence-transformers/all-MiniLM-L6-v2`)**:
   - Converts natural-language policy questions into 384-dimensional dense semantic embeddings.
   - Pretrained model cached locally; inference executed on CPU with L2 normalization.
2. **FAISS Vector Index (`IndexFlatIP`)**:
   - Efficient dense similarity search retrieving Top-$K$ candidate cached questions.
   - Exact inner product computation over unit-norm vectors ($\langle \mathbf{u}, \mathbf{v} \rangle = \cos(\mathbf{u}, \mathbf{v})$).
3. **Logistic Regression Equivalence Classifier**:
   - Trained on balanced and hard-negative policy query pairs.
   - Evaluates 8 handcrafted features: cosine similarity, token Jaccard lexical overlap, character length difference, numeric difference, numeric contradiction indicator, category mismatch indicator, jurisdiction mismatch indicator, and negation mismatch indicator.
4. **Isotonic Regression Probability Calibrator**:
   - Non-parametric monotonic calibrator fit on a held-out calibration split (preventing topic leakage).
   - Maps raw decision values into true posterior match probabilities $P(\text{equivalent} \mid s)$.
5. **Statistical Threshold Safety (Clopper-Pearson Exact Binomial Bound)**:
   - Evaluates candidate thresholds $\tau$ against held-out validation data.
   - Computes one-sided 95% confidence upper bound for False-Hit Rate (FHR):
     $$\text{UCB} = \text{Beta.ppf}(1 - \alpha, k + 1, n - k)$$
   - Conservative fallback mode is enforced if evaluation evidence is insufficient to guarantee $\text{FHR} \le 1.0\%$.
6. **K-Means Clustering Topic Discovery**:
   - Unsupervised clustering of employee queries for administrator analytics and recurring inquiry discovery.
   - Does not dictate safety decisions.

---

## 2. Grounded Extractive Answer Service (Zero Paid API Keys Required)

CacheMind includes an internal, provider-independent extractive answer engine:
- Extracts exact authoritative clauses directly from administrator-approved policy documents.
- Returns grounded answers with source document titles, policy IDs, versions, and clause citations.
- If no supported answer exists in approved policy documents, it informs the user that no supported policy was found.
- Modular provider interface allows plug-in of optional external LLM endpoints (Grok / OpenAI) if keys are provided in settings.

---

## 3. Two Distinct User Roles & Backend RBAC

Security is strictly enforced in the FastAPI backend (`backend/app/api/deps.py`) via bcrypt password hashing and JWT access tokens:

### A. Employee User Workspace (`/` or `/app`)
- **Natural-Language Chat Interface**: Submit inquiries and receive instant answers.
- **Explicit Badges**: High-contrast `CACHE HIT` (e.g. 4.2 ms) or `CACHE MISS` (grounded search) indicators.
- **Source Citations**: Clearly displays source document name, policy code, version, and excerpt.
- **Answer Feedback & Reporting**: Thumbs up / thumbs down helpfulness ratings, and a 1-click modal to report outdated or incorrect answers to admins.
- **Personal History & Favorites**: Search personal query history, mark frequently used answers as favorites, or delete personal logs.
- **Personal Analytics**: View personal queries answered, cache-hit ratio, and latency metrics.
- **Data Isolation**: Users can never view another user's queries, private conversations, or system-wide admin tools.

### B. Administrator Governance Portal (`/admin`)
- **User Management**: View all accounts, toggle active/inactive status, and change roles (`USER` $\leftrightarrow$ `ADMIN`).
- **Policy & Document Governance**:
  - Upload documents (`.txt`, `.pdf`, `.md`).
  - **Document Preview Drawer**: Inspect extracted clauses, detected domain, and metadata before publishing.
  - Policy versioning and deprecation.
  - **Invalidate Obsolete Cache**: Prunes cache entries linked to obsolete or deactivated policies.
- **Synthetic Dataset Generation**:
  - Automatically synthesize labeled positive and adversarial negative pairs from active policies.
  - Inspect and edit candidate pairs prior to training.
  - Upload custom CSV question-pair datasets.
- **Model Registry & 1-Click Rollback**:
  - Trigger training, calibration, and threshold evaluation with versioned snapshots.
  - Inspect active Logistic Regression feature weights and calibrator status.
  - Atomic 1-click rollback to any previously archived model snapshot.
- **Feedback & Reported Answers Queue**: Audit user reports, update status (`PENDING`, `REVIEWED`, `RESOLVED`, `DISMISSED`), and attach admin notes.
- **Audit Trail & Governance**: Complete query logs with similarity scores, calibrated probabilities, and 1-click **Export to CSV**.
- **System Settings**: Configure acceptance thresholds, cache expiry, and external API keys.

---

## 4. Quickstart Guide (Windows PowerShell)

### Prerequisites
- Python 3.10+ (Verified on Python 3.11.9)
- Node.js 18+ and npm (Verified on Node v24.16.0)

### 1-Click Launch
Run the automated launcher from the project root:
```powershell
.\start.ps1
```
*(Or double-click `start.bat`)*

Both FastAPI backend (`http://127.0.0.1:8000`) and Vite frontend (`http://localhost:5173`) will launch automatically in separate terminal windows.

---

### Manual Step-by-Step Setup

#### Step 1: Backend Environment & Dependencies
```powershell
cd c:\projects\CacheMind\backend
pip install -r requirements.txt
```

#### Step 2: Initialize Database, Seed Policies & Train Models
```powershell
# Seeds default accounts (admin / user), policies, and verified cache entries:
python -m app.services.seed_service

# Trains Logistic Regression, fits Isotonic Calibrator, and snapshots registry:
python -m app.services.training_service
```

#### Step 3: Run Backend Tests
Run the complete automated pytest suite (26/26 tests passing):
```powershell
python -m pytest -v
```

#### Step 4: Start Backend Server
```powershell
python app/main.py
```
- API Endpoint: `http://127.0.0.1:8000`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`

#### Step 5: Start Frontend
In a new PowerShell terminal:
```powershell
cd c:\projects\CacheMind\frontend
npm install
npm run test     # Runs 6/6 Vitest unit and component tests
npm run dev      # Launches dev server at http://localhost:5173
```

---

## 5. Pre-Configured Demo Credentials

For instant evaluation, the database is pre-seeded with two accounts:

| Role | Username | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **User** | `user` | `User@123` | Employee chat, citations, personal history, favorites, reporting |
| **Admin** | `admin` | `Admin@123` | Complete governance portal, model registry, policy editor, user management |

The login page (`/login`) also includes **1-Click Quick Demo** buttons for instant access without manual typing.

---

## 6. Automated Test Suites

### Backend Tests (`pytest`, 26 Tests Passing)
- `tests/test_auth_rbac.py` (6 tests): Registration, bcrypt authentication, JWT token generation, 403 Forbidden enforcement on admin routes, user query history isolation, user favorites & feedback submission.
- `tests/test_e2e_api.py` (7 tests): Health check, dashboard summary, cache hit verification, numerical adversarial rejection, category adversarial rejection, conversational filler optimization, K-Means clustering.
- `tests/test_ml_stats.py` (2 tests): Exact Clopper-Pearson binomial confidence bounds, feature engineering calculation.
- `tests/test_model_registry_rollback.py` (3 tests): Model registry listing & rollback, document preview & versioning, synthetic data candidate generation.
- `tests/test_safety.py` (8 tests): Deterministic policy guardrails (numerical bounds, jurisdiction matching, employee category matching, negation detection, version consistency).

### Frontend Tests (`vitest`, 6 Tests Passing)
- `src/__tests__/auth.test.ts`: LocalStorage token management and client-side role guards.
- `src/__tests__/cache_decision.test.ts`: Latency verification, cache hit/miss badges, and statistical bound verification.
- `src/__tests__/auth_page.test.tsx`: Component rendering, branding, and Quick Demo buttons.

---

## 7. License & Credits

Built for enterprise AI governance and cost optimization.
Synthetic sample data represents fictional entities (Kaveri Tech Solutions Pvt. Ltd., Tamil Nadu, India) for safe demonstration.
