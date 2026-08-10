import json
import os
from typing import Any, Dict, List, Tuple

import numpy as np


class IndexStore:
    def __init__(self, run_id: str, out_dir: str):
        self.run_id = run_id
        # Note: out_dir corresponds to OUTPUT_DIR/runs. We put index in <run_id>/index
        self.index_dir = os.path.join(out_dir, "index")
        self.meta_path = os.path.join(self.index_dir, "metadata.json")
        self.vec_path = os.path.join(self.index_dir, "vectors.npy")
        
        # in-memory structures
        self.metadata: List[Dict[str, Any]] = []
        self.vectors: np.ndarray = np.empty((0, 0))
        
        self.load()

    def load(self):
        if os.path.exists(self.meta_path) and os.path.exists(self.vec_path):
            with open(self.meta_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
            self.vectors = np.load(self.vec_path)

    def save(self):
        os.makedirs(self.index_dir, exist_ok=True)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)
        np.save(self.vec_path, self.vectors)

    def add_documents(self, documents: List[Dict[str, Any]], embeddings: List[List[float]]):
        if not documents or not embeddings:
            return
            
        # Ensure we don't duplicate existing item IDs if called multiple times naively.
        # But we'll trust the pipeline logic for now.
        new_vecs = np.array(embeddings, dtype=np.float32)
        if self.vectors.size == 0:
            self.vectors = new_vecs
        else:
            if self.vectors.shape[1] != new_vecs.shape[1]:
                print(f"⚠️ Index dimension mismatch ({self.vectors.shape[1]} vs {new_vecs.shape[1]}). Clearing index as a result of embedding fallback.")
                self.vectors = new_vecs
                self.metadata = []
            else:
                self.vectors = np.vstack([self.vectors, new_vecs])
            
        self.metadata.extend(documents)
        self.save()

    def search(self, query_emb: List[float], top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        if self.vectors.size == 0 or len(self.metadata) == 0:
            return []
            
        q_vec = np.array(query_emb, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []
            
        v_norms = np.linalg.norm(self.vectors, axis=1)
        valid_mask = v_norms > 0
        
        similarities = np.zeros(self.vectors.shape[0])
        safe_v_norms = np.where(valid_mask, v_norms, 1.0)
        
        similarities[valid_mask] = np.dot(self.vectors[valid_mask], q_vec) / (safe_v_norms[valid_mask] * q_norm)
        
        top_k = min(top_k, len(similarities))
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            results.append((self.metadata[idx], float(similarities[idx])))
            
        return results

_store_cache = {}

def get_index_store(run_id: str, out_dir: str) -> IndexStore:
    # out_dir passed here is the run's specific output dir (e.g. outputs/runs/<run_id>)
    if run_id not in _store_cache:
        _store_cache[run_id] = IndexStore(run_id, out_dir)
    return _store_cache[run_id]
