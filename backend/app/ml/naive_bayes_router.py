import joblib
import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from sklearn.naive_bayes import MultinomialNB, GaussianNB
from sklearn.feature_extraction.text import TfidfVectorizer

from app.core.config import settings

DOMAIN_TRAINING_CORPUS = [
    # HR queries
    ("How many days of annual leave and privilege leave are available?", "HR"),
    ("What is the maternity leave duration and benefits for women?", "HR"),
    ("Are contractors eligible for paid sick leave and casual leave?", "HR"),
    ("Can employees work from home up to 2 days per week?", "HR"),
    ("What are the cafeteria meal subsidy rates and food vouchers?", "HR"),
    ("Do employees working second shifts get cab transport and dinner?", "HR"),
    ("What is the probation period and confirmation process?", "HR"),
    ("How long is the resignation notice period for permanent staff?", "HR"),
    ("What is the bereavement and compassionate leave policy?", "HR"),
    ("What is the employee relocation grant and packers allowance?", "HR"),
    
    # IT queries
    ("How do I request a company laptop or monitor upgrade?", "IT"),
    ("What is the monthly broadband and high speed internet reimbursement?", "IT"),
    ("What are the security guidelines for bringing personal BYOD devices?", "IT"),
    ("How do I connect to the corporate VPN from home?", "IT"),
    ("What are the password rotation and multi factor authentication rules?", "IT"),
    ("How do I report a lost office access security badge?", "IT"),
    ("Can I install unauthorized software on my work laptop?", "IT"),
    
    # FINANCE queries
    ("What is the daily travel allowance and per diem for domestic trips?", "FINANCE"),
    ("What is the maximum hotel accommodation limit for tier 1 cities?", "FINANCE"),
    ("How do I submit GST tax invoices for business expenses?", "FINANCE"),
    ("What is the corporate food card Sodexo Pluxee monthly allocation?", "FINANCE"),
    ("When is the annual performance bonus and gratuity disbursed?", "FINANCE"),
    ("How is the Provident Fund PF and ESI deducted from salary?", "FINANCE"),
    ("What is the medical insurance sum insured for employee family?", "FINANCE"),
    
    # LEGAL queries
    ("What are the compliance rules under Tamil Nadu Shops and Establishments Act?", "LEGAL"),
    ("What is the non disclosure agreement NDA policy for client projects?", "LEGAL"),
    ("What is the POSH policy for workplace harassment prevention?", "LEGAL"),
    ("Who owns the intellectual property created during employment?", "LEGAL"),
    ("What is the conflict of interest and moonlight policy?", "LEGAL")
]

class NaiveBayesDomainRouter:
    """
    Syllabus Model: Bayesian Learning (Naïve Bayes Classifier)
    Applies Bayes' Theorem to classify user questions into corporate policy domains
    (HR, IT, FINANCE, LEGAL) and computes posterior class probabilities P(Domain | Query).
    """
    def __init__(self, model_path: Optional[Path] = None, vec_path: Optional[Path] = None):
        self.model_path = model_path or (settings.MODELS_DIR / "naive_bayes_domain_router.joblib")
        self.vec_path = vec_path or (settings.MODELS_DIR / "naive_bayes_vectorizer.joblib")
        self.model: Optional[MultinomialNB] = None
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.is_fitted = False
        self.load_or_train()

    def load_or_train(self):
        if self.model_path.exists() and self.vec_path.exists():
            try:
                self.model = joblib.load(self.model_path)
                self.vectorizer = joblib.load(self.vec_path)
                self.is_fitted = True
                print("[NaiveBayes] Loaded trained Naïve Bayes Domain Classifier.")
                return
            except Exception as e:
                print(f"[NaiveBayes] Error loading artifacts: {e}. Retraining...")

        self.train_default()

    def train_default(self):
        """Fits Naïve Bayes classifier on domain corpus."""
        texts = [item[0] for item in DOMAIN_TRAINING_CORPUS]
        labels = [item[1] for item in DOMAIN_TRAINING_CORPUS]

        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", lowercase=True)
        X = self.vectorizer.fit_transform(texts)

        self.model = MultinomialNB(alpha=1.0) # Laplace smoothing
        self.model.fit(X, labels)
        self.is_fitted = True

        settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.vectorizer, self.vec_path)
        print(f"[NaiveBayes] Successfully trained and saved Naïve Bayes Router on {len(texts)} samples.")

    def predict_domain(self, query: str) -> Tuple[str, float, Dict[str, float]]:
        """
        Calculates posterior probability P(Domain | Query) using Bayes' Theorem.
        Returns: (best_domain, best_probability, all_probabilities_dict)
        """
        if not self.is_fitted or self.model is None or self.vectorizer is None:
            return "HR", 0.5, {"HR": 0.5, "IT": 0.2, "FINANCE": 0.2, "LEGAL": 0.1}

        vec = self.vectorizer.transform([query])
        probs = self.model.predict_proba(vec)[0]
        classes = self.model.classes_

        prob_dict = {str(c): float(round(p, 4)) for c, p in zip(classes, probs)}
        best_idx = probs.argmax()
        best_domain = str(classes[best_idx])
        best_prob = float(probs[best_idx])

        return best_domain, best_prob, prob_dict

naive_bayes_router = NaiveBayesDomainRouter()
