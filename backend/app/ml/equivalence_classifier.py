import os
import joblib
import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
)
from app.core.config import settings
from app.ml.feature_engineering import FEATURE_NAMES

class EquivalenceClassifierService:
    def __init__(self, model_path: Optional[Path] = None, meta_path: Optional[Path] = None):
        self.model_path = model_path or (settings.MODELS_DIR / "equivalence_classifier.joblib")
        self.meta_path = meta_path or (settings.MODELS_DIR / "equivalence_classifier_meta.json")
        self.pipeline: Optional[Pipeline] = None
        self.metadata: Dict[str, Any] = {}
        self.load()

    def load(self):
        if self.model_path.exists() and self.meta_path.exists():
            try:
                self.pipeline = joblib.load(self.model_path)
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                print("Loaded fitted Logistic Regression Equivalence Classifier.")
                return
            except Exception as e:
                print(f"Failed to load classifier: {e}")
        self.pipeline = None
        self.metadata = {
            "status": "uninitialized",
            "feature_names": FEATURE_NAMES,
            "metrics": {}
        }

    @property
    def is_fitted(self) -> bool:
        return self.pipeline is not None

    def train(self, X: np.ndarray, y: np.ndarray, C: float = 1.0) -> Dict[str, Any]:
        """
        Trains Logistic Regression pipeline with StandardScaler.
        Calculates train metrics (precision, recall, f1, roc_auc, confusion matrix).
        """
        if len(np.unique(y)) < 2:
            raise ValueError("Training requires at least two distinct classes (0 and 1).")

        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(C=C, class_weight="balanced", random_state=42, max_iter=1000))
        ])

        pipeline.fit(X, y)
        self.pipeline = pipeline

        # Compute training metrics
        y_pred = pipeline.predict(X)
        y_prob = pipeline.predict_proba(X)[:, 1]

        cm = confusion_matrix(y, y_pred).tolist()
        metrics = {
            "precision": float(precision_score(y, y_pred, zero_division=0)),
            "recall": float(recall_score(y, y_pred, zero_division=0)),
            "f1": float(f1_score(y, y_pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y, y_prob)) if len(np.unique(y)) > 1 else 0.0,
            "confusion_matrix": cm,
            "sample_count": int(len(y))
        }

        # Extract coefficients
        lr_clf = pipeline.named_steps["clf"]
        coef_dict = dict(zip(FEATURE_NAMES, lr_clf.coef_[0].tolist()))

        self.metadata = {
            "status": "ready",
            "model_type": "StandardScaler + LogisticRegression",
            "hyperparameters": {"C": C, "class_weight": "balanced", "random_state": 42},
            "coefficients": coef_dict,
            "intercept": float(lr_clf.intercept_[0]),
            "feature_names": FEATURE_NAMES,
            "metrics": metrics
        }

        # Save artifacts
        settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, str(self.model_path))
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

        return self.metadata

    def predict_score(self, feature_vector: np.ndarray) -> float:
        """
        Returns raw decision probability P(equivalent=1) in [0, 1].
        """
        if not self.is_fitted:
            # Fallback if model not trained yet: use the cosine similarity feature directly
            return float(np.clip(feature_vector[0], 0.0, 1.0))
        
        X = feature_vector.reshape(1, -1)
        prob = self.pipeline.predict_proba(X)[0, 1]
        return float(prob)

equivalence_classifier = EquivalenceClassifierService()
