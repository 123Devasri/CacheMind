import os
import joblib
import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss
from app.core.config import settings

class ProbabilityCalibrationService:
    def __init__(self, model_path: Optional[Path] = None, meta_path: Optional[Path] = None):
        self.model_path = model_path or (settings.MODELS_DIR / "isotonic_calibrator.joblib")
        self.meta_path = meta_path or (settings.MODELS_DIR / "isotonic_calibrator_meta.json")
        self.calibrator: Optional[IsotonicRegression] = None
        self.metadata: Dict[str, Any] = {}
        self.load()

    def load(self):
        if self.model_path.exists() and self.meta_path.exists():
            try:
                self.calibrator = joblib.load(self.model_path)
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                print("Loaded fitted Isotonic Regression Calibrator.")
                return
            except Exception as e:
                print(f"Failed to load calibrator: {e}")
        self.calibrator = None
        self.metadata = {
            "status": "uninitialized",
            "metrics": {}
        }

    @property
    def is_fitted(self) -> bool:
        return self.calibrator is not None

    def fit(self, raw_scores: np.ndarray, y_true: np.ndarray) -> Dict[str, Any]:
        """
        Fits Isotonic Regression on a dedicated calibration dataset.
        Enforces monotonic increasing mapping: y_cal in [0, 1].
        """
        if len(raw_scores) < 5:
            raise ValueError("At least 5 calibration samples are required to fit isotonic regression.")
        if len(np.unique(y_true)) < 2:
            raise ValueError("Calibration set must contain both positive and negative instances.")

        iso = IsotonicRegression(y_min=0.0, y_max=1.0, increasing=True, out_of_bounds="clip")
        iso.fit(raw_scores, y_true)
        self.calibrator = iso

        calibrated_preds = iso.predict(raw_scores)
        brier_before = float(brier_score_loss(y_true, raw_scores))
        brier_after = float(brier_score_loss(y_true, calibrated_preds))

        self.metadata = {
            "status": "ready",
            "model_type": "IsotonicRegression",
            "sample_count": int(len(raw_scores)),
            "brier_score_before": brier_before,
            "brier_score_after": brier_after,
            "brier_improvement": brier_before - brier_after
        }

        settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.calibrator, self.model_path)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

        return self.metadata

    def calibrate(self, raw_score: float) -> float:
        """
        Calibrates raw score into a well-calibrated posterior probability in [0, 1].
        """
        if not self.is_fitted:
            # Fallback if uncalibrated: clip raw score
            return float(np.clip(raw_score, 0.0, 1.0))
        
        cal_score = self.calibrator.predict(np.array([raw_score]))[0]
        return float(np.clip(cal_score, 0.0, 1.0))

probability_calibrator = ProbabilityCalibrationService()
