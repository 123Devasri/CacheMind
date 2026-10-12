import os
import json
import numpy as np
import faiss
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from app.core.config import settings

class FAISSIndexService:
    """
    FAISS similarity search using Inner Product (Cosine similarity with normalized vectors).
    Complexity: O(N * D) for exact brute-force search (IndexFlatIP), ensuring 100% recall
    for enterprise cache sizes without approximation quantization loss.
    """
    def __init__(self, index_file: Optional[Path] = None, map_file: Optional[Path] = None):
        self.index_file = index_file or (settings.INDEXES_DIR / "faiss_cache.index")
        self.map_file = map_file or (settings.INDEXES_DIR / "faiss_id_map.json")
        self.dim = settings.EMBEDDING_DIM
        
        self.index: Optional[faiss.IndexFlatIP] = None
        self.id_map: Dict[int, str] = {} # faiss_vector_id -> cached_entry_uuid
        self.load_or_create()

    def load_or_create(self):
        if self.index_file.exists() and self.map_file.exists():
            try:
                self.index = faiss.read_index(str(self.index_file))
                with open(self.map_file, "r", encoding="utf-8") as f:
                    # JSON keys are strings, convert back to int
                    raw_map = json.load(f)
                    self.id_map = {int(k): v for k, v in raw_map.items()}
                print(f"Loaded existing FAISS index with {self.index.ntotal} vectors.")
                return
            except Exception as e:
                print(f"Failed to load FAISS index from disk, creating fresh: {e}")

        # Create IndexFlatIP
        self.index = faiss.IndexFlatIP(self.dim)
        self.id_map = {}

    def save(self):
        settings.INDEXES_DIR.mkdir(parents=True, exist_ok=True)
        if self.index is not None:
            faiss.write_index(self.index, str(self.index_file))
            with open(self.map_file, "w", encoding="utf-8") as f:
                json.dump(self.id_map, f, indent=2)

    def total_vectors(self) -> int:
        return self.index.ntotal if self.index is not None else 0

    def rebuild_index(self, entry_ids: List[str], embeddings: np.ndarray):
        """
        Rebuilds FAISS index completely from provided normalized embeddings and IDs.
        """
        assert len(entry_ids) == len(embeddings), "ID count and vector count mismatch"
        
        # Fresh FlatIP index
        self.index = faiss.IndexFlatIP(self.dim)
        self.id_map = {}

        if len(entry_ids) > 0:
            embeddings_f32 = np.ascontiguousarray(embeddings, dtype=np.float32)
            self.index.add(embeddings_f32)
            for idx, entry_id in enumerate(entry_ids):
                self.id_map[idx] = entry_id

        self.save()
        return self.index.ntotal

    def add_vector(self, entry_id: str, embedding: np.ndarray) -> int:
        """
        Adds a single normalized vector to the index.
        Returns the assigned faiss_id.
        """
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.dim)

        vector_f32 = np.ascontiguousarray(embedding.reshape(1, -1), dtype=np.float32)
        next_id = self.index.ntotal
        self.index.add(vector_f32)
        self.id_map[next_id] = entry_id
        self.save()
        return next_id

    def search(
        self, query_vector: np.ndarray, top_k: int = 5, min_similarity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Searches top-K candidates using inner product (cosine similarity).
        Returns list of dicts: [{"faiss_id": int, "entry_id": str, "similarity": float}]
        """
        if self.index is None or self.index.ntotal == 0:
            return []

        vector_f32 = np.ascontiguousarray(query_vector.reshape(1, -1), dtype=np.float32)
        k = min(top_k, self.index.ntotal)
        
        distances, indices = self.index.search(vector_f32, k)
        
        results = []
        for sim, idx in zip(distances[0], indices[0]):
            if idx != -1 and sim >= min_similarity:
                entry_id = self.id_map.get(int(idx))
                if entry_id:
                    results.append({
                        "faiss_id": int(idx),
                        "entry_id": entry_id,
                        "similarity": float(sim)
                    })
        return results

faiss_service = FAISSIndexService()
