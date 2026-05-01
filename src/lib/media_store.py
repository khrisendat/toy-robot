import json
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "recordings")
)


class MediaStore:
    def __init__(self, base_dir: str = _DEFAULT_DIR):
        self._base = os.path.abspath(base_dir)
        self._log = os.path.join(self._base, "log.jsonl")

    def save_audio(self, wav_bytes: bytes, speaker_name: Optional[str] = None) -> str:
        path = self._make_path("audio", "wav")
        self._write(path, wav_bytes)
        self._log_entry({"type": "audio", "file": path, "speaker": speaker_name})
        logger.debug(f"[Media] Saved audio: {path}")
        return path

    def save_image(self, jpeg_bytes: bytes) -> str:
        path = self._make_path("image", "jpg")
        self._write(path, jpeg_bytes)
        self._log_entry({"type": "image", "file": path})
        logger.debug(f"[Media] Saved image: {path}")
        return path

    def _make_path(self, label: str, ext: str) -> str:
        now = datetime.now()
        day_dir = os.path.join(self._base, now.strftime("%Y-%m-%d"))
        os.makedirs(day_dir, exist_ok=True)
        filename = f"{now.strftime('%H%M%S')}_{label}.{ext}"
        return os.path.join(day_dir, filename)

    def _write(self, path: str, data: bytes) -> None:
        try:
            with open(path, "wb") as f:
                f.write(data)
        except Exception as e:
            logger.error(f"[Media] Failed to write {path}: {e}")

    def _log_entry(self, entry: dict) -> None:
        entry["timestamp"] = datetime.now().isoformat(timespec="seconds")
        try:
            with open(self._log, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"[Media] Failed to write log: {e}")
