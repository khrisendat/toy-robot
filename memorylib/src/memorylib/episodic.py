import json
import logging
import os
from datetime import datetime
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_MODEL_NAME = "all-MiniLM-L6-v2"


class EpisodicStore:
    """
    Append-only episodic memory with semantic search.

    Entries are persisted as JSONL. Embeddings are stored inline so the
    matrix is rebuilt from disk on startup without recomputing them.

    The sentence-transformer model is lazy-loaded on first store/search.
    """

    def __init__(self, path: str):
        self._path = os.path.abspath(path)
        self._model = None
        self._entries: list[dict] = []   # all persisted entries
        self._indexed: list[dict] = []   # subset with valid embeddings
        self._matrix: Optional[np.ndarray] = None  # (N, D) — 1:1 with _indexed
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(self, text: str, metadata: Optional[dict] = None) -> None:
        """Embed and persist a text entry."""
        self._ensure_model()
        embedding = self._embed(text)
        entry: dict = {
            "id": datetime.now().isoformat(timespec="seconds"),
            "text": text,
            "embedding": embedding.tolist(),
        }
        if metadata:
            entry["metadata"] = metadata
        self._entries.append(entry)
        self._indexed.append(entry)
        self._rebuild_matrix()
        self._append_entry(entry)

    def search(self, query: str, top_k: int = 3) -> list[str]:
        """Return the top_k most semantically similar entry texts."""
        if self._matrix is None or not self._indexed:
            return []
        self._ensure_model()
        q = self._embed(query)
        scores = self._matrix @ q
        k = min(top_k, len(self._indexed))
        top_idx = np.argpartition(scores, -k)[-k:]
        top_idx = top_idx[np.argsort(scores[top_idx])[::-1]]
        return [self._indexed[i]["text"] for i in top_idx]

    def all_entries(self) -> list[dict]:
        """Return all persisted entries (id, text, metadata)."""
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ensure_model(self) -> None:
        if self._model is None:
            logger.info(f"[Episodic] Loading embedding model '{_MODEL_NAME}'...")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(_MODEL_NAME)

    def _embed(self, text: str) -> np.ndarray:
        return self._model.encode(text, normalize_embeddings=True).astype(np.float32)

    def _rebuild_matrix(self) -> None:
        if not self._indexed:
            self._matrix = None
            return
        vectors = [np.array(e["embedding"], dtype=np.float32) for e in self._indexed]
        self._matrix = np.stack(vectors)

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    self._entries.append(entry)
                    if "embedding" in entry:
                        vec = np.array(entry["embedding"], dtype=np.float32)
                        if np.isfinite(vec).all():
                            self._indexed.append(entry)
            self._rebuild_matrix()
            logger.debug(f"[Episodic] Loaded {len(self._entries)} entries from {self._path}")
        except Exception as e:
            logger.error(f"[Episodic] Failed to load {self._path}: {e}")

    def _append_entry(self, entry: dict) -> None:
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"[Episodic] Failed to write entry: {e}")
