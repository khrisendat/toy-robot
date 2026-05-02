import io
import json
import logging
import os
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_THRESHOLD = 0.6  # L2 distance; lower = more similar


def _jpeg_to_array(jpeg_bytes: bytes) -> np.ndarray:
    from PIL import Image
    return np.array(Image.open(io.BytesIO(jpeg_bytes)))


class FaceStore:
    """
    Face-profile store for person identification from images.

    Enrolls named people from JPEG images, then identifies faces in new images
    using L2 distance on face_recognition encodings (128-dim dlib vectors).

    face_recognition is imported lazily — it is an optional dependency.
    """

    def __init__(self, path: str):
        self.path = os.path.abspath(path)
        self._profiles: dict = {}  # name -> list[np.ndarray]
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enroll(self, name: str, jpeg_bytes: bytes) -> int:
        """Encode all faces in the image and store under name."""
        encodings = self._encode(jpeg_bytes)
        if not encodings:
            logger.warning(f"[Face] No face detected in enrollment image for '{name}'")
            return len(self._profiles.get(name, []))
        for enc in encodings:
            self._profiles.setdefault(name, []).append(enc)
            self._append(name, enc)
        count = len(self._profiles[name])
        logger.info(f"[Face] Enrolled '{name}' ({len(encodings)} face(s), {count} total)")
        return count

    def identify(self, jpeg_bytes: bytes, threshold: float = _DEFAULT_THRESHOLD) -> Optional[str]:
        """Return the closest matching name for any face found, or None."""
        if not self._profiles:
            return None
        encodings = self._encode(jpeg_bytes)
        if not encodings:
            return None

        all_names = []
        all_encs = []
        for name, encs in self._profiles.items():
            for enc in encs:
                all_names.append(name)
                all_encs.append(enc)

        known = np.array(all_encs)
        best_name, best_dist = None, float("inf")
        for unknown in encodings:
            distances = np.linalg.norm(known - np.array(unknown), axis=1)
            idx = int(np.argmin(distances))
            if distances[idx] < best_dist:
                best_dist = distances[idx]
                best_name = all_names[idx]

        if best_dist < threshold:
            logger.info(f"[Face] Identified '{best_name}' (distance={best_dist:.3f})")
            return best_name
        logger.info(f"[Face] Unknown face (best={best_name}, distance={best_dist:.3f})")
        return None

    def faces(self) -> list:
        return list(self._profiles.keys())

    def sample_count(self, name: str) -> int:
        return len(self._profiles.get(name, []))

    @classmethod
    def profiles_exist(cls, path: str) -> bool:
        return os.path.exists(path)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _encode(self, jpeg_bytes: bytes) -> list:
        import face_recognition
        image = _jpeg_to_array(jpeg_bytes)
        return face_recognition.face_encodings(image)

    def _append(self, name: str, encoding: np.ndarray) -> None:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "a") as f:
                f.write(json.dumps({"name": name, "encoding": encoding.tolist()}) + "\n")
        except Exception as e:
            logger.error(f"[Face] Failed to write {self.path}: {e}")

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
                    encoding = np.array(entry["encoding"], dtype=np.float64)
                    self._profiles.setdefault(name, []).append(encoding)
            logger.info(f"[Face] Loaded profiles for: {list(self._profiles)}")
        except Exception as e:
            logger.error(f"[Face] Failed to load {self.path}: {e}")
