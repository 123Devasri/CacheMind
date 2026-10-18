import joblib
import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score, f1_score

from app.core.config import settings

class EquivalenceKNNClassifier:
    """
    Syllabus Model: Instance-Based Learning (k-Nearest Neighbor Classifier)
    Predicts question equivalence based on majority voting of k nearest feature vectors.
    """
    def __init__(self, model_path: Optional[Path] = None, meta_path: Optional[Path] = None):
        self.model_path = model_path or (settings.MODELS_DIR / "knn_classifier.joblib")
        self.meta_path = meta_path or (settings.MODELS_DIR / "knn_classifier_meta.json")
        self.model: Optional[KNeighborsClassifier] = None
        self.metadata: Dict[str, Any] = {}
        self.is_fitted = False
        self.load()

    def load(self):
        if self.model_path.exists():
            try:
                self.model = joblib.load(self.model_path)
                self.is_fitted = True
                if self.meta_path.exists():
                    with open(self.meta_path, "r", encoding="utf-8") as f:
                        self.metadata = json.load(f)
                print(f"[k-NN] Loaded fitted k-Nearest Neighbor Classifier from {self.model_path.name}")
            except Exception as e:
                print(f"[k-NN] Error loading k-NN: {e}. Model requires training.")
                self.model = None
                self.is_fitted = False
        else:
            self.model = None
            self.is_fitted = False

    def train(self, X: np.ndarray, y: np.ndarray, n_neighbors: int = 5, metric: str = "minkowski") -> Dict[str, Any]:
        """
        Trains k-NN classifier on 8-D handcrafted feature representations.
        """
        assert len(X) == len(y), "Features and labels dimension mismatch."
        k = min(n_neighbors, len(X))

        self.model = KNeighborsClassifier(
            n_neighbors=k,
            weights="distance", # Weight neighbors by inverse distance
            metric=metric
        )
        self.model.fit(X, y)
        self.is_fitted = True

        preds = self.model.predict(X)
        acc = float(accuracy_score(y, preds))
        f1 = float(f1_score(y, preds, zero_division=0))

        self.metadata = {
            "model_type": "k_nearest_neighbors",
            "n_neighbors": k,
            "metric": metric,
            "weights": "distance",
            "metrics": {
                "accuracy": acc,
                "f1": f1
            },
            "training_samples": len(X)
        }

        settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, self.model_path)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

        print(f"[k-NN] Fitted k-Nearest Neighbor Classifier (k={k}, Acc: {acc:.4f})")
        return self.metadata

    def predict_score(self, features: np.ndarray) -> float:
        """
        Returns equivalence probability P(Equivalent | features) in [0.0, 1.0].
        """
        cos_sim = float(features[0])
        num_conflict = float(features[6]) if len(features) > 6 else 0.0
        neg_conflict = float(features[7]) if len(features) > 7 else 0.0
        if cos_sim >= 0.98 and num_conflict == 0.0 and neg_conflict == 0.0:
            return 1.0

        if not self.is_fitted or self.model is None:
            return float(features[0])

        x = features.reshape(1, -1)
        probs = self.model.predict_proba(x)
        if probs.shape[1] > 1:
            return float(probs[0, 1])
        return float(probs[0, 0])

knn_classifier = EquivalenceKNNClassifier()
