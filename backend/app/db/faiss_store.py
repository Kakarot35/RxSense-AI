"""
FAISS vector store wrapper.
Stores embeddings + metadata separately (FAISS doesn't store metadata natively).
"""
import faiss
import numpy as np
import pickle, os
from pathlib import Path
from sentence_transformers import SentenceTransformer
import structlog

log = structlog.get_logger()

INDEX_PATH = Path("./faiss_index/drug.index")
META_PATH  = Path("./faiss_index/drug.meta.pkl")
EMBED_MODEL = "all-MiniLM-L6-v2"
DIM = 384   # all-MiniLM-L6-v2 output dimension

class FAISSStore:
    def __init__(self):
        self._model = SentenceTransformer(EMBED_MODEL)
        self._index: faiss.IndexFlatIP | None = None
        self._metadata: list[dict] = []
        self._documents: list[str] = []
        self._load_if_exists()

    def _load_if_exists(self):
        if INDEX_PATH.exists() and META_PATH.exists():
            self._index = faiss.read_index(str(INDEX_PATH))
            with open(META_PATH, "rb") as f:
                saved = pickle.load(f)
            self._metadata = saved["metadata"]
            self._documents = saved["documents"]
            log.info("faiss.loaded", vectors=self._index.ntotal)
        else:
            # Inner product index (use normalised vectors → cosine similarity)
            self._index = faiss.IndexHNSWFlat(DIM, 32)
            self._index.hnsw.efConstruction = 200
            log.info("faiss.created_new")

    def save(self):
        INDEX_PATH.parent.mkdir(exist_ok=True)
        faiss.write_index(self._index, str(INDEX_PATH))
        with open(META_PATH, "wb") as f:
            pickle.dump({"metadata": self._metadata, "documents": self._documents}, f)
        log.info("faiss.saved", vectors=self._index.ntotal)

    def add(self, documents: list[str], metadatas: list[dict]):
        embeddings = self._embed(documents)
        self._index.add(embeddings)
        self._documents.extend(documents)
        self._metadata.extend(metadatas)

    def search(self, query: str, k: int = 5, drug_filter: str | None = None) -> list[dict]:
        """
        Returns top-k results as list of {text, metadata, score}.
        Applies drug_filter if provided (post-filter since FAISS has no native metadata filter).
        """
        q_embed = self._embed([query])
        # Search more candidates if filtering, to ensure k results after filter
        fetch_k = k * 4 if drug_filter else k
        scores, indices = self._index.search(q_embed, min(fetch_k, self._index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            meta = self._metadata[idx]
            if drug_filter and meta.get("drug") != drug_filter.lower():
                continue
            results.append({
                "text": self._documents[idx],
                "metadata": meta,
                "score": float(score),   # inner product of normalised = cosine similarity
            })
            if len(results) >= k:
                break

        return results

    def _embed(self, texts: list[str]) -> np.ndarray:
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.astype(np.float32)

faiss_store = FAISSStore()
