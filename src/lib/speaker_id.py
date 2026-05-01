import io
import json
import logging
import os
import wave
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "speakers.json")
)
_DEFAULT_THRESHOLD = 0.75


def _wav_to_array(wav_bytes: bytes) -> tuple[np.ndarray, int]:
    with io.BytesIO(wav_bytes) as f:
        with wave.open(f) as wf:
            sr = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    return samples, sr


class SpeakerIdentifier:
    def __init__(self, path: str = _DEFAULT_PATH):
        self.path = os.path.abspath(path)
        self._encoder = None  # loaded lazily to avoid import cost at startup
        self._profiles: dict[str, list[np.ndarray]] = {}
        self._load()

    def enroll(self, name: str, wav_bytes: bytes) -> int:
        """Embed wav_bytes and store under name. Returns total sample count."""
        embedding = self._embed(wav_bytes)
        self._profiles.setdefault(name, []).append(embedding)
        self._save()
        count = len(self._profiles[name])
        logger.info(f"[SpeakerID] Enrolled '{name}' (sample {count})")
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
            logger.info(f"[SpeakerID] Identified '{best_name}' (score={best_score:.3f})")
            return best_name
        logger.info(f"[SpeakerID] Unknown speaker (best={best_name}, score={best_score:.3f})")
        return None

    def speakers(self) -> list[str]:
        return list(self._profiles.keys())

    @classmethod
    def profiles_exist(cls, path: str = _DEFAULT_PATH) -> bool:
        return os.path.exists(path)

    def sample_count(self, name: str) -> int:
        return len(self._profiles.get(name, []))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _embed(self, wav_bytes: bytes) -> np.ndarray:
        from resemblyzer import VoiceEncoder, preprocess_wav  # lazy import
        if self._encoder is None:
            logger.info("[SpeakerID] Loading VoiceEncoder...")
            self._encoder = VoiceEncoder()
        samples, sr = _wav_to_array(wav_bytes)
        wav = preprocess_wav(samples, source_sr=sr)
        return self._encoder.embed_utterance(wav)

    def _save(self) -> None:
        data = {name: [e.tolist() for e in embs] for name, embs in self._profiles.items()}
        try:
            with open(self.path, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"[SpeakerID] Failed to save {self.path}: {e}")

    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path) as f:
                data = json.load(f)
            self._profiles = {
                name: [np.array(e, dtype=np.float32) for e in embs]
                for name, embs in data.items()
            }
            logger.info(f"[SpeakerID] Loaded profiles for: {list(self._profiles)}")
        except Exception as e:
            logger.error(f"[SpeakerID] Failed to load {self.path}: {e}")
