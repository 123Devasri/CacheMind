import numpy as np
from typing import List, Dict, Any, Optional
from collections import Counter
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from app.ml.policy_validation import normalize_text

class QueryClusteringService:
    def __init__(self):
        pass

    def cluster_queries(
        self,
        questions: List[str],
        embeddings: np.ndarray,
        n_clusters: int = 4
    ) -> Dict[str, Any]:
        """
        Clusters stored query embeddings using scikit-learn K-Means.
        Includes 2D PCA projection for visualization and keyword extraction for cluster labeling.
        Note: Clustering is strictly an analytics workflow and NEVER approves cache hits.
        """
        n_samples = len(questions)
        if n_samples < 2:
            return {
                "status": "insufficient_data",
                "message": f"Clustering requires at least 2 queries; got {n_samples}.",
                "clusters": [],
                "points": []
            }

        k = max(2, min(n_clusters, n_samples))
        
        # Run KMeans
        kmeans = KMeans(n_clusters=k, random_state=42, n_init="auto")
        labels = kmeans.fit_predict(embeddings)

        # 2D PCA projection for visualization
        if n_samples >= 2:
            pca = PCA(n_components=2, random_state=42)
            coords_2d = pca.fit_transform(embeddings)
        else:
            coords_2d = np.zeros((n_samples, 2))

        # Build cluster summaries
        clusters = []
        for c_id in range(k):
            member_indices = [i for i, lbl in enumerate(labels) if lbl == c_id]
            member_questions = [questions[i] for i in member_indices]
            
            # Simple keyword frequency for cluster title
            words = []
            for q in member_questions:
                words.extend([w for w in normalize_text(q).split() if len(w) > 3 and w not in {"what", "when", "how", "many", "does", "have", "with", "from"}])
            common_words = [w for w, _ in Counter(words).most_common(4)]
            cluster_name = f"Cluster {c_id + 1}: " + (", ".join(common_words).title() if common_words else "General Queries")

            clusters.append({
                "cluster_id": c_id,
                "name": cluster_name,
                "size": len(member_indices),
                "representative_questions": member_questions[:5],
                "keywords": common_words
            })

        points = []
        for i, q in enumerate(questions):
            points.append({
                "question": q,
                "cluster_id": int(labels[i]),
                "x": float(round(coords_2d[i, 0], 4)),
                "y": float(round(coords_2d[i, 1], 4))
            })

        return {
            "status": "completed",
            "cluster_count": k,
            "total_queries": n_samples,
            "clusters": clusters,
            "points": points
        }

query_clusterer = QueryClusteringService()
