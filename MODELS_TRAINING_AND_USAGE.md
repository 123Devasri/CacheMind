# CacheMind — Machine Learning Models: Training, Runtime Usage & Artifact Directory

This document details every machine learning, deep learning, statistical, and generative model used in **CacheMind**, specifying the exact code files where each model is trained, where it is used during runtime inference, where its serialized artifacts are saved, its hyperparameters, and its role in the system.

---

## 1. Complete Model Master Table

| Model Name | Architectural Family | Training Code File | Runtime / Inference Code File | Serialized Artifact Location | Primary Dataset / Inputs |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SentenceTransformer** | Bi-Encoder Transformer (`all-MiniLM-L6-v2`) | Pretrained (`Hugging Face`) | [`backend/app/ml/embeddings.py`](file:///c:/projects/CacheMind/backend/app/ml/embeddings.py) | Local HF Cache / CPU weights | Raw natural language queries and policy chunk text |
| **FAISS Vector Index** | Dense Vector Search (`IndexFlatIP`) | [`backend/app/ml/faiss_index.py`](file:///c:/projects/CacheMind/backend/app/ml/faiss_index.py) | [`backend/app/ml/faiss_index.py`](file:///c:/projects/CacheMind/backend/app/ml/faiss_index.py) | [`backend/artifacts/indexes/faiss_cache.index`](file:///c:/projects/CacheMind/backend/artifacts/indexes/faiss_cache.index)<br>[`backend/artifacts/indexes/faiss_id_map.json`](file:///c:/projects/CacheMind/backend/artifacts/indexes/faiss_id_map.json) | 384-dimensional normalized question embeddings |
| **Decision Tree Classifier** | Supervised Learning (ID3 / CART) | [`backend/app/ml/decision_tree_classifier.py`](file:///c:/projects/CacheMind/backend/app/ml/decision_tree_classifier.py)<br>[`backend/app/services/training_service.py`](file:///c:/projects/CacheMind/backend/app/services/training_service.py) | [`backend/app/ml/decision_tree_classifier.py`](file:///c:/projects/CacheMind/backend/app/ml/decision_tree_classifier.py)<br>[`backend/app/ml/cache_pipeline.py`](file:///c:/projects/CacheMind/backend/app/ml/cache_pipeline.py) | [`backend/artifacts/models/decision_tree_classifier.joblib`](file:///c:/projects/CacheMind/backend/artifacts/models/decision_tree_classifier.joblib)<br>[`backend/artifacts/models/decision_tree_classifier_meta.json`](file:///c:/projects/CacheMind/backend/artifacts/models/decision_tree_classifier_meta.json) | 8-D pairwise feature vectors from `train` split |
| **$k$-Nearest Neighbor Classifier** | Instance-Based Learning ($k$-NN) | [`backend/app/ml/knn_classifier.py`](file:///c:/projects/CacheMind/backend/app/ml/knn_classifier.py)<br>[`backend/app/services/training_service.py`](file:///c:/projects/CacheMind/backend/app/services/training_service.py) | [`backend/app/ml/knn_classifier.py`](file:///c:/projects/CacheMind/backend/app/ml/knn_classifier.py)<br>[`backend/app/ml/cache_pipeline.py`](file:///c:/projects/CacheMind/backend/app/ml/cache_pipeline.py) | [`backend/artifacts/models/knn_classifier.joblib`](file:///c:/projects/CacheMind/backend/artifacts/models/knn_classifier.joblib)<br>[`backend/artifacts/models/knn_classifier_meta.json`](file:///c:/projects/CacheMind/backend/artifacts/models/knn_classifier_meta.json) | 8-D pairwise feature vectors from `train` split |
| **Logistic Regression Classifier** | Linear Classifier Baseline | [`backend/app/ml/equivalence_classifier.py`](file:///c:/projects/CacheMind/backend/app/ml/equivalence_classifier.py)<br>[`backend/app/services/training_service.py`](file:///c:/projects/CacheMind/backend/app/services/training_service.py) | [`backend/app/ml/equivalence_classifier.py`](file:///c:/projects/CacheMind/backend/app/ml/equivalence_classifier.py)<br>[`backend/app/ml/cache_pipeline.py`](file:///c:/projects/CacheMind/backend/app/ml/cache_pipeline.py) | [`backend/artifacts/models/equivalence_classifier.joblib`](file:///c:/projects/CacheMind/backend/artifacts/models/equivalence_classifier.joblib)<br>[`backend/artifacts/models/equivalence_classifier_meta.json`](file:///c:/projects/CacheMind/backend/artifacts/models/equivalence_classifier_meta.json) | 8-D pairwise feature vectors from `train` split |
| **Isotonic Probability Calibrator** | Non-parametric Calibration (PAVA) | [`backend/app/ml/probability_calibration.py`](file:///c:/projects/CacheMind/backend/app/ml/probability_calibration.py)<br>[`backend/app/services/training_service.py`](file:///c:/projects/CacheMind/backend/app/services/training_service.py) | [`backend/app/ml/probability_calibration.py`](file:///c:/projects/CacheMind/backend/app/ml/probability_calibration.py)<br>[`backend/app/ml/cache_pipeline.py`](file:///c:/projects/CacheMind/backend/app/ml/cache_pipeline.py) | [`backend/artifacts/models/isotonic_calibrator.joblib`](file:///c:/projects/CacheMind/backend/artifacts/models/isotonic_calibrator.joblib)<br>[`backend/artifacts/models/isotonic_calibrator_meta.json`](file:///c:/projects/CacheMind/backend/artifacts/models/isotonic_calibrator_meta.json) | Raw decision scores from dedicated `calibration` split |
| **Naïve Bayes Domain Router** | Bayesian Learning (`MultinomialNB`) | [`backend/app/ml/naive_bayes_router.py`](file:///c:/projects/CacheMind/backend/app/ml/naive_bayes_router.py) | [`backend/app/ml/query_optimizer.py`](file:///c:/projects/CacheMind/backend/app/ml/query_optimizer.py) | [`backend/artifacts/models/naive_bayes_domain_router.joblib`](file:///c:/projects/CacheMind/backend/artifacts/models/naive_bayes_domain_router.joblib)<br>[`backend/artifacts/models/naive_bayes_vectorizer.joblib`](file:///c:/projects/CacheMind/backend/artifacts/models/naive_bayes_vectorizer.joblib) | Labeled corporate domain query corpus (`HR`, `IT`, `FINANCE`, `LEGAL`) |
| **Query Clustering & Projection** | Unsupervised Learning ($K$-Means + PCA) | [`backend/app/ml/query_clustering.py`](file:///c:/projects/CacheMind/backend/app/ml/query_clustering.py) | [`backend/app/api/routes.py`](file:///c:/projects/CacheMind/backend/app/api/routes.py) (`/api/ml/clusters`) | Dynamic (In-Memory / Admin UI Response) | Stored 384-D query embeddings from SQLite `CachedEntry` |
| **Generative LLM (Grok API)** | Frontier LLM (xAI / Groq API) | Pretrained Foundation Model | [`backend/app/services/grok_service.py`](file:///c:/projects/CacheMind/backend/app/services/grok_service.py)<br>[`backend/app/services/fallback_service.py`](file:///c:/projects/CacheMind/backend/app/services/fallback_service.py) | Hosted Cloud API (`xAI` / `api.groq.com`) | Top-$K$ retrieved contextual evidence chunks from admin documents |

---

## 2. In-Depth Technical Specification for Each Model

### 1. Dense Semantic Embeddings: `SentenceTransformer`
- **Model Identifier**: `sentence-transformers/all-MiniLM-L6-v2`
- **Implementation File**: [`backend/app/ml/embeddings.py`](file:///c:/projects/CacheMind/backend/app/ml/embeddings.py)
- **Class / Methods**: `EmbeddingService.encode(text, normalize=True)`
- **Where It Is Used in Code**:
  - In [`backend/app/ml/cache_pipeline.py`](file:///c:/projects/CacheMind/backend/app/ml/cache_pipeline.py#L146) to embed incoming user queries for FAISS candidate retrieval.
  - In [`backend/app/services/rag_service.py`](file:///c:/projects/CacheMind/backend/app/services/rag_service.py#L188-L192) to embed contextual chunks and search evidence in policy documents.
  - In [`backend/app/ml/faiss_index.py`](file:///c:/projects/CacheMind/backend/app/ml/faiss_index.py) to generate index vectors for newly cached questions.
  - In [`backend/app/services/training_service.py`](file:///c:/projects/CacheMind/backend/app/services/training_service.py#L51) for batch encoding unique question pairs during offline training.
- **Dimensionality**: 384-dimensional dense float32 vector, L2-normalized ($\|\mathbf{v}\|_2 = 1.0$).

---

### 2. Fast Vector Retrieval: `FAISS IndexFlatIP`
- **Implementation File**: [`backend/app/ml/faiss_index.py`](file:///c:/projects/CacheMind/backend/app/ml/faiss_index.py)
- **Class / Methods**: `FAISSService.search()`, `FAISSService.add_entry()`, `FAISSService.rebuild()`
- **Where It Is Trained / Built**:
  - Initialized / rebuilt from active SQLite records in [`backend/app/services/seed_service.py`](file:///c:/projects/CacheMind/backend/app/services/seed_service.py#L463) and [`backend/app/api/routes.py`](file:///c:/projects/CacheMind/backend/app/api/routes.py#L160) upon selective policy invalidation.
- **Where It Is Used in Runtime**:
  - In [`backend/app/ml/cache_pipeline.py`](file:///c:/projects/CacheMind/backend/app/ml/cache_pipeline.py#L149-L154) to perform sub-millisecond retrieval of the top 5 nearest cached questions with cosine similarity $\ge 0.65$.
- **Artifacts Saved**:
  - Binary index: `backend/artifacts/indexes/faiss_cache.index`
  - ID map: `backend/artifacts/indexes/faiss_id_map.json`

---

### 3. Equivalence Classifier A: Decision Tree Classifier (Syllabus Model)
- **Model Architecture**: ID3 / CART Decision Tree (`sklearn.tree.DecisionTreeClassifier`)
- **Code File**: [`backend/app/ml/decision_tree_classifier.py`](file:///c:/projects/CacheMind/backend/app/ml/decision_tree_classifier.py)
- **Class / Methods**: `EquivalenceDecisionTreeClassifier.train()`, `predict_proba()`, `predict_score()`
- **Where It Is Trained**:
  - Trained in [`backend/app/services/training_service.py`](file:///c:/projects/CacheMind/backend/app/services/training_service.py#L119) on 8-D handcrafted feature vectors from the `train` split of `enterprise_policy_pairs_split.csv`.
- **Where It Is Used in Runtime**:
  - Default active equivalence model in [`backend/app/ml/equivalence_classifier.py`](file:///c:/projects/CacheMind/backend/app/ml/equivalence_classifier.py#L31). Invoked during Step 8 of [`backend/app/ml/cache_pipeline.py`](file:///c:/projects/CacheMind/backend/app/ml/cache_pipeline.py#L207) to compute the equivalence score.
- **Hyperparameters**:
  - `criterion="entropy"` (Shannon Information Gain)
  - `max_depth=5` (prevents overfitting and ensures interpretable rule depth)
  - `min_samples_split=4`
  - `min_samples_leaf=2`
- **Artifacts Saved**:
  - `backend/artifacts/models/decision_tree_classifier.joblib`
  - `backend/artifacts/models/decision_tree_classifier_meta.json`

---

### 4. Equivalence Classifier B: $k$-Nearest Neighbor Classifier (Syllabus Model)
- **Model Architecture**: Instance-Based Learning (`sklearn.neighbors.KNeighborsClassifier`)
- **Code File**: [`backend/app/ml/knn_classifier.py`](file:///c:/projects/CacheMind/backend/app/ml/knn_classifier.py)
- **Class / Methods**: `EquivalenceKNNClassifier.train()`, `predict_proba()`, `predict_score()`
- **Where It Is Trained**:
  - Trained in [`backend/app/services/training_service.py`](file:///c:/projects/CacheMind/backend/app/services/training_service.py#L78) on the same 8-D feature vector representations from the `train` split.
- **Where It Is Used in Runtime**:
  - Selectable via the Model Registry in [`backend/app/ml/equivalence_classifier.py`](file:///c:/projects/CacheMind/backend/app/ml/equivalence_classifier.py#L34-L41).
- **Hyperparameters**:
  - `n_neighbors=5`
  - `weights="distance"` (inverse distance weighting)
  - `metric="minkowski"`
- **Artifacts Saved**:
  - `backend/artifacts/models/knn_classifier.joblib`
  - `backend/artifacts/models/knn_classifier_meta.json`

---

### 5. Equivalence Classifier C: L2-Regularized Logistic Regression
- **Model Architecture**: Linear Classifier Pipeline (`StandardScaler` + `LogisticRegression`)
- **Code File**: [`backend/app/ml/equivalence_classifier.py`](file:///c:/projects/CacheMind/backend/app/ml/equivalence_classifier.py)
- **Class / Methods**: `EquivalenceClassifierService.train()`, `predict_score()`
- **Where It Is Trained**:
  - Trained in [`backend/app/services/training_service.py`](file:///c:/projects/CacheMind/backend/app/services/training_service.py#L81-L86) on the `train` split.
- **Where It Is Used in Runtime**:
  - Selectable via the Model Registry in [`backend/app/ml/equivalence_classifier.py`](file:///c:/projects/CacheMind/backend/app/ml/equivalence_classifier.py).
- **Hyperparameters**:
  - `C=1.0` (L2 penalty)
  - `class_weight="balanced"`
  - `max_iter=1000`
- **Artifacts Saved**:
  - `backend/artifacts/models/equivalence_classifier.joblib`
  - `backend/artifacts/models/equivalence_classifier_meta.json`

---

### 6. Probability Calibration: `IsotonicRegression`
- **Model Architecture**: Non-Parametric Monotonic Regression using PAVA (`sklearn.isotonic.IsotonicRegression`)
- **Code File**: [`backend/app/ml/probability_calibration.py`](file:///c:/projects/CacheMind/backend/app/ml/probability_calibration.py)
- **Class / Methods**: `ProbabilityCalibrationService.fit()`, `calibrate()`
- **Where It Is Trained / Fitted**:
  - Fitted in [`backend/app/services/training_service.py`](file:///c:/projects/CacheMind/backend/app/services/training_service.py#L125) on raw decision scores generated from the dedicated `calibration` split of `enterprise_policy_pairs_split.csv`.
- **Where It Is Used in Runtime**:
  - Step 9 in [`backend/app/ml/cache_pipeline.py`](file:///c:/projects/CacheMind/backend/app/ml/cache_pipeline.py#L210) to map the raw score from the active classifier into an empirically sound probability $P_{\text{cal}} \in [0, 1]$.
- **Hyperparameters**:
  - `y_min=0.0`, `y_max=1.0`
  - `increasing=True`
  - `out_of_bounds="clip"`
- **Artifacts Saved**:
  - `backend/artifacts/models/isotonic_calibrator.joblib`
  - `backend/artifacts/models/isotonic_calibrator_meta.json`

---

### 7. Domain Routing: Multinomial Naïve Bayes (Syllabus Model)
- **Model Architecture**: Bayesian Learning (`sklearn.naive_bayes.MultinomialNB` with `TfidfVectorizer`)
- **Code File**: [`backend/app/ml/naive_bayes_router.py`](file:///c:/projects/CacheMind/backend/app/ml/naive_bayes_router.py)
- **Class / Methods**: `NaiveBayesDomainRouter.train_default()`, `predict_domain()`
- **Where It Is Trained**:
  - Trained in [`backend/app/ml/naive_bayes_router.py`](file:///c:/projects/CacheMind/backend/app/ml/naive_bayes_router.py#L76-L92) over labeled corporate domain training corpus (`DOMAIN_TRAINING_CORPUS`).
- **Where It Is Used in Runtime**:
  - Called by the Query Optimizer in [`backend/app/ml/query_optimizer.py`](file:///c:/projects/CacheMind/backend/app/ml/query_optimizer.py#L240) to route incoming queries to the appropriate policy domain (`HR`, `IT`, `FINANCE`, `LEGAL`) and provide posterior probabilities.
- **Hyperparameters**:
  - `alpha=1.0` (Laplace additive smoothing)
  - `ngram_range=(1, 2)` (Unigrams and bigrams)
  - `stop_words="english"`, `lowercase=True`
- **Artifacts Saved**:
  - `backend/artifacts/models/naive_bayes_domain_router.joblib`
  - `backend/artifacts/models/naive_bayes_vectorizer.joblib`

---

### 8. Topic Discovery & Visualization: $K$-Means Clustering & PCA
- **Model Architecture**: Unsupervised Clustering & Dimensionality Reduction (`sklearn.cluster.KMeans`, `sklearn.decomposition.PCA`)
- **Code File**: [`backend/app/ml/query_clustering.py`](file:///c:/projects/CacheMind/backend/app/ml/query_clustering.py)
- **Class / Methods**: `QueryClusteringService.cluster_queries()`
- **Where It Is Used**:
  - Evaluated in [`backend/app/services/training_service.py`](file:///c:/projects/CacheMind/backend/app/services/training_service.py#L153-L160) and served via API endpoint `GET /api/ml/clusters` in [`backend/app/api/routes.py`](file:///c:/projects/CacheMind/backend/app/api/routes.py) to provide administrator topic discovery and interactive 2D cluster scatter plots.
- **Hyperparameters**:
  - `n_clusters=min(5, len(questions))`
  - `n_init="auto"`, `random_state=42`
  - `PCA(n_components=2)`

---

### 9. Generative LLM: Official xAI Grok API & Groq Fallback
- **Model Architecture**: Frontier Generative Transformer (`grok-2-latest`, `grok-beta`, or Groq Cloud `openai/gpt-oss-120b`)
- **Code File**: [`backend/app/services/grok_service.py`](file:///c:/projects/CacheMind/backend/app/services/grok_service.py)
- **Class / Methods**: `GrokService.generate_grounded_answer()`
- **Where It Is Used in Runtime**:
  - Invoked strictly on **cache misses** in [`backend/app/ml/cache_pipeline.py`](file:///c:/projects/CacheMind/backend/app/ml/cache_pipeline.py#L268-L286) via [`backend/app/services/fallback_service.py`](file:///c:/projects/CacheMind/backend/app/services/fallback_service.py).
- **Configuration & Parameters**:
  - System Prompt: [`GROK_SYSTEM_INSTRUCTION`](file:///c:/projects/CacheMind/backend/app/services/grok_service.py#L13-L28) strictly binds generation to retrieved policy chunk evidence.
  - `temperature=0.0`
  - Tracks exact token counts and compute cost:
    - Input: $\$2.00$ per 1M prompt tokens
    - Output: $\$10.00$ per 1M completion tokens

---

## 3. Model Registry & 1-Click Rollback Architecture

CacheMind implements a versioned **Model Registry** with atomic rollback capability.

- **Snapshot Directory**: `backend/artifacts/models/registry/v1.0.<timestamp>/`
- **Code Implementation**: [`backend/app/services/training_service.py`](file:///c:/projects/CacheMind/backend/app/services/training_service.py#L203-L260) and [`backend/app/api/routes.py`](file:///c:/projects/CacheMind/backend/app/api/routes.py#L230-L270)
- **Snapshot Contents**:
  1. `decision_tree_classifier.joblib`
  2. `knn_classifier.joblib`
  3. `equivalence_classifier.joblib`
  4. `isotonic_calibrator.joblib`
  5. `faiss_cache.index`
  6. `faiss_id_map.json`
- **Rollback Mechanism**: When an administrator triggers a rollback to a previous version tag, CacheMind copies all 6 artifacts back to `backend/artifacts/models/` and `backend/artifacts/indexes/`, updates the active record in `ModelArtifactVersion`, and reloads in-memory classifiers without server restart.
