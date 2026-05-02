import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class MediaStore:
    """
    Stores audio and image files to disk with a JSONL manifest.

    Files are organised as: {base_dir}/{YYYY-MM-DD}/{HHMMSS}_{label}.{ext}
    Each write appends one line to {base_dir}/log.jsonl.
    """

    def __init__(self, base_dir: str):
        self._base = os.path.abspath(base_dir)
        self._log = os.path.join(self._base, "log.jsonl")

    def save_audio(self, wav_bytes: bytes, **tags) -> str:
        """Write WAV bytes and return the file path."""
        path = self._make_path("audio", "wav")
        self._write(path, wav_bytes)
        self._log_entry({"type": "audio", "file": path, **tags})
        logger.debug(f"[Media] Saved audio: {path}")
        return path

    def save_image(self, jpeg_bytes: bytes, **tags) -> str:
        """Write JPEG bytes and return the file path."""
        path = self._make_path("image", "jpg")
        self._write(path, jpeg_bytes)
        self._log_entry({"type": "image", "file": path, **tags})
        logger.debug(f"[Media] Saved image: {path}")
        return path

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _make_path(self, label: str, ext: str) -> str:
        now = datetime.now()
        day_dir = os.path.join(self._base, now.strftime("%Y-%m-%d"))
        os.makedirs(day_dir, exist_ok=True)
        return os.path.join(day_dir, f"{now.strftime('%H%M%S')}_{label}.{ext}")

    def _write(self, path: str, data: bytes) -> None:
        try:
            with open(path, "wb") as f:
                f.write(data)
        except Exception as e:
            logger.error(f"[Media] Failed to write {path}: {e}")

    def read_log(self) -> list[dict]:
        """Return all manifest entries."""
        if not os.path.exists(self._log):
            return []
        entries = []
        with open(self._log) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def rewrite_log(self, entries: list[dict]) -> None:
        """Overwrite the manifest with a modified entry list."""
        os.makedirs(self._base, exist_ok=True)
        with open(self._log, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    def _log_entry(self, entry: dict) -> None:
        entry["timestamp"] = datetime.now().isoformat(timespec="seconds")
        try:
            os.makedirs(self._base, exist_ok=True)
            with open(self._log, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"[Media] Failed to write log: {e}")
