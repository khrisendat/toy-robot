import json
import logging
import os
import time
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

MEMORY_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "memory.json")
MODEL_NAME = "all-MiniLM-L6-v2"


class MemoryStore:
    def __init__(self, path: str = MEMORY_PATH):
        self.path = os.path.abspath(path)
        self._model = None
        self._entries: list[dict] = []        # [{id, text, embedding, timestamp}]
        self._matrix: Optional[np.ndarray] = None  # (N, D) float32

        self._load_model()
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 3) -> list[str]:
        """Return the top_k most relevant memory texts for the given query."""
        if self._matrix is None or len(self._entries) == 0:
            return []

        q = self._embed(query)
        scores = self._matrix @ q  # cosine similarity (vectors are unit-normalised)
        k = min(top_k, len(self._entries))
        top_indices = np.argpartition(scores, -k)[-k:]
        top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]
        return [self._entries[i]["text"] for i in top_indices]

    def store(self, user_text: str, robot_text: str) -> None:
        """Persist a conversation turn to memory."""
        text = f"Child: {user_text} Robot: {robot_text}"
        embedding = self._embed(text)

        entry = {
            "id": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "text": text,
            "embedding": embedding.tolist(),
        }
        self._entries.append(entry)
        self._rebuild_matrix()
        self._save()
        logger.debug(f"[Memory] Stored turn. Total entries: {len(self._entries)}")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_model(self) -> None:
        logger.info(f"[Memory] Loading embedding model '{MODEL_NAME}'...")
        start = time.time()
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(MODEL_NAME)
        logger.info(f"[Memory] Model loaded in {time.time() - start:.2f}s")

    def _embed(self, text: str) -> np.ndarray:
        vec = self._model.encode(text, normalize_embeddings=True)
        return vec.astype(np.float32)

    def _rebuild_matrix(self) -> None:
        if not self._entries:
            self._matrix = None
            return
        self._matrix = np.stack(
            [np.array(e["embedding"], dtype=np.float32) for e in self._entries]
        )

    def _load(self) -> None:
        if not os.path.exists(self.path):
            logger.info("[Memory] No existing memory file found. Starting fresh.")
            return
        try:
            with open(self.path) as f:
                self._entries = json.load(f)
            self._rebuild_matrix()
            logger.info(f"[Memory] Loaded {len(self._entries)} memories from {self.path}")
        except Exception as e:
            logger.error(f"[Memory] Failed to load memory file: {e}")
            self._entries = []

    def _save(self) -> None:
        try:
            with open(self.path, "w") as f:
                json.dump(self._entries, f)
        except Exception as e:
            logger.error(f"[Memory] Failed to save memory file: {e}")
