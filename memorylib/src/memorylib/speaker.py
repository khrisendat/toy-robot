import io
import json
import logging
import os
import wave
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_THRESHOLD = 0.75


def _wav_to_array(wav_bytes: bytes) -> tuple:
    """Decode WAV bytes to a float32 sample array and sample rate."""
    with io.BytesIO(wav_bytes) as f:
        with wave.open(f) as wf:
            sr = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    return samples, sr


class SpeakerStore:
    """
    Voice-profile store for speaker identification.

    Enrolls named speakers from WAV audio, then identifies speakers from
    new audio using cosine similarity on resemblyzer embeddings.

    resemblyzer is imported lazily on first embed call so the module can be
    imported without it installed (it's an optional dependency).
    """

    def __init__(self, path: str):
        self.path = os.path.abspath(path)
        self._encoder = None
        self._profiles: dict = {}  # name -> list[np.ndarray]
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enroll(self, name: str, wav_bytes: bytes) -> int:
        """Embed wav_bytes and append to the store. Returns total sample count."""
        embedding = self._embed(wav_bytes)
        self._profiles.setdefault(name, []).append(embedding)
        self._append(name, embedding)
        count = len(self._profiles[name])
        logger.info(f"[Speaker] Enrolled '{name}' (sample {count})")
        return count

    def identify(self, wav_bytes: bytes, threshold: float = _DEFAULT_THRESHOLD) -> Optional[str]:
        """Return the best-matching speaker name, or None if below threshold."""
        if not self._profiles:
            return None
        embedding = self._embed(wav_bytes)
        best_name, best_score = None, -1.0
        for name, embeddings in self._profiles.items():
            score = max(float(np.dot(embedding, e)) for e in embeddings)
            if score > best_score:
                best_name, best_score = name, score
        if best_score >= threshold:
            logger.info(f"[Speaker] Identified '{best_name}' (score={best_score:.3f})")
            return best_name
        logger.info(f"[Speaker] Unknown speaker (best={best_name}, score={best_score:.3f})")
        return None

    def speakers(self) -> list:
        return list(self._profiles.keys())

    def sample_count(self, name: str) -> int:
        return len(self._profiles.get(name, []))

    @classmethod
    def profiles_exist(cls, path: str) -> bool:
        return os.path.exists(path)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _embed(self, wav_bytes: bytes) -> np.ndarray:
        from resemblyzer import VoiceEncoder, preprocess_wav
        if self._encoder is None:
            logger.info("[Speaker] Loading VoiceEncoder...")
            self._encoder = VoiceEncoder()
        samples, sr = _wav_to_array(wav_bytes)
        wav = preprocess_wav(samples, source_sr=sr)
        return self._encoder.embed_utterance(wav)

    def _append(self, name: str, embedding: np.ndarray) -> None:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "a") as f:
                f.write(json.dumps({"name": name, "embedding": embedding.tolist()}) + "\n")
        except Exception as e:
            logger.error(f"[Speaker] Failed to write {self.path}: {e}")

    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    name = entry["name"]
                    embedding = np.array(entry["embedding"], dtype=np.float32)
                    self._profiles.setdefault(name, []).append(embedding)
            logger.info(f"[Speaker] Loaded profiles for: {list(self._profiles)}")
        except Exception as e:
            logger.error(f"[Speaker] Failed to load {self.path}: {e}")
