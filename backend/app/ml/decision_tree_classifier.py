import joblib
import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

from app.core.config import settings
from app.ml.feature_engineering import FEATURE_NAMES

class EquivalenceDecisionTreeClassifier:
    """
    Syllabus Model: Decision Tree Learning (ID3 / CART)
    Evaluates multi-feature equivalence between incoming query and cached question.
    Learns hierarchical, auditable if-else rules for enterprise policy compliance.
    """
    def __init__(self, model_path: Optional[Path] = None, meta_path: Optional[Path] = None):
        self.model_path = model_path or (settings.MODELS_DIR / "decision_tree_classifier.joblib")
        self.meta_path = meta_path or (settings.MODELS_DIR / "decision_tree_classifier_meta.json")
        self.model: Optional[DecisionTreeClassifier] = None
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
                print(f"[DecisionTree] Loaded fitted Decision Tree Classifier from {self.model_path.name}")
            except Exception as e:
                print(f"[DecisionTree] Error loading Decision Tree: {e}. Model requires training.")
                self.model = None
                self.is_fitted = False
        else:
            self.model = None
            self.is_fitted = False

    def train(self, X: np.ndarray, y: np.ndarray, criterion: str = "entropy", max_depth: int = 5) -> Dict[str, Any]:
        """
        Trains Decision Tree on 8-D handcrafted feature vectors.
        Uses criterion='entropy' (ID3 information gain) or 'gini'.
        """
        assert len(X) == len(y), "Features and labels dimension mismatch."
        assert len(X) > 0, "Empty training dataset."

        # Train with entropy (ID3 style) or gini
        self.model = DecisionTreeClassifier(
            criterion=criterion,
            max_depth=max_depth,
            min_samples_split=4,
            min_samples_leaf=2,
            random_state=42
        )
        self.model.fit(X, y)
        self.is_fitted = True

        # Metrics on training data
        preds = self.model.predict(X)
        probs = self.model.predict_proba(X)[:, 1] if self.model.n_classes_ > 1 else preds.astype(float)

        acc = float(accuracy_score(y, preds))
        prec = float(precision_score(y, preds, zero_division=0))
        rec = float(recall_score(y, preds, zero_division=0))
        f1 = float(f1_score(y, preds, zero_division=0))
        try:
            auc = float(roc_auc_score(y, probs))
        except Exception:
            auc = 1.0

        # Feature importances
        importances = {name: float(imp) for name, imp in zip(FEATURE_NAMES, self.model.feature_importances_)}

        # Human-readable decision tree rules
        tree_rules = export_text(self.model, feature_names=FEATURE_NAMES)

        self.metadata = {
            "model_type": "decision_tree_id3",
            "criterion": criterion,
            "max_depth": max_depth,
            "feature_names": FEATURE_NAMES,
            "feature_importances": importances,
            "tree_rules": tree_rules,
            "metrics": {
                "accuracy": acc,
                "precision": prec,
                "recall": rec,
                "f1": f1,
                "roc_auc": auc
            },
            "training_samples": len(X)
        }

        # Save artifacts
        settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, self.model_path)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

        print(f"[DecisionTree] Trained Decision Tree (Accuracy: {acc:.4f}, F1: {f1:.4f})")
        return self.metadata

    def predict_score(self, features: np.ndarray) -> float:
        """
        Returns probability score P(Equivalent | features) in [0.0, 1.0].
        """
        # Identity / near-identity fast-path: identical or near-identical text with zero policy conflicts
        cos_sim = float(features[0])
        num_conflict = float(features[6]) if len(features) > 6 else 0.0
        neg_conflict = float(features[7]) if len(features) > 7 else 0.0
        if cos_sim >= 0.98 and num_conflict == 0.0 and neg_conflict == 0.0:
            return 1.0

        if not self.is_fitted or self.model is None:
            # Fallback to pure cosine similarity if model not trained
            return float(features[0])

        x = features.reshape(1, -1)
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(x)
            if probs.shape[1] > 1:
                return float(probs[0, 1])
            return float(probs[0, 0])
        return float(self.model.predict(x)[0])

    def export_rules(self) -> str:
        if self.is_fitted and self.model is not None:
            return export_text(self.model, feature_names=FEATURE_NAMES)
        return "Decision tree model is not yet fitted."

decision_tree_classifier = EquivalenceDecisionTreeClassifier()
