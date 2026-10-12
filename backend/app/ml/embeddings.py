import os
import torch
import numpy as np
from typing import List, Union
from sentence_transformers import SentenceTransformer
from app.core.config import settings

class EmbeddingService:
    _instance = None
    _model = None
    _device = "cpu"

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()

    def _load_model(self):
        try:
            print(f"Loading SentenceTransformer: {settings.EMBEDDING_MODEL_NAME} on {self._device}...")
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME, device=self._device)
            print("SentenceTransformer loaded successfully.")
        except Exception as e:
            print(f"Error loading SentenceTransformer: {e}")
            self._model = None

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    @property
    def model_info(self) -> dict:
        return {
            "model_name": settings.EMBEDDING_MODEL_NAME,
            "embedding_dim": settings.EMBEDDING_DIM,
            "device": self._device,
            "is_ready": self.is_ready
        }

    def encode(self, texts: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        """
        Generates 384-dimensional embeddings normalized for cosine similarity via inner product.
        """
        if not self.is_ready:
            raise RuntimeError(
                f"Embedding model '{settings.EMBEDDING_MODEL_NAME}' is not loaded. "
                "Ensure internet access for initial download or pre-download the model."
            )

        if isinstance(texts, str):
            if not texts.strip():
                return np.zeros((settings.EMBEDDING_DIM,), dtype=np.float32)
            texts = [texts]
        elif len(texts) == 0:
            return np.empty((0, settings.EMBEDDING_DIM), dtype=np.float32)

        # Handle empty strings within list
        cleaned_texts = [t if t.strip() else "empty_query" for t in texts]

        embeddings = self._model.encode(
            cleaned_texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=normalize
        )
        return embeddings.astype(np.float32)

embedding_service = EmbeddingService.get_instance()
