import json
import logging
import os
import re

from .memory import MemoryStore

logger = logging.getLogger(__name__)

_MEMORY_BLOCK_RE = re.compile(r'\[MEMORY\s+[^\]]+\]')
_STORE_TYPE_RE = re.compile(r'\[MEMORY\s+(profile|preference)\s+')
_KV_RE = re.compile(r'([\w_]+)="([^"]+)"')
_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def strip_annotations(text: str) -> str:
    return _MEMORY_BLOCK_RE.sub("", text).strip()


class KVStore:
    """Flat key-value store persisted as a JSON object."""

    def __init__(self, path: str):
        self.path = os.path.abspath(path)
        self._data: dict = {}
        self._load()

    def set(self, key: str, value: str) -> None:
        self._data[key] = value
        self._save()

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def items(self):
        return list(self._data.items())

    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path) as f:
                self._data = json.load(f)
        except Exception as e:
            logger.error(f"[KVStore] Failed to load {self.path}: {e}")

    def _save(self) -> None:
        try:
            with open(self.path, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            logger.error(f"[KVStore] Failed to save {self.path}: {e}")


class MemoryManager:
    """Orchestrates three memory stores:
    - profile:     stable facts about the child and robot (always injected)
    - preferences: likes, dislikes, fears (always injected)
    - episodic:    past conversation turns (retrieved by semantic similarity)
    """

    def __init__(self, base_dir: str = _BASE_DIR):
        base = os.path.abspath(base_dir)
        self.episodic = MemoryStore(os.path.join(base, "memory.json"))
        self.profile = KVStore(os.path.join(base, "profile.json"))
        self.preferences = KVStore(os.path.join(base, "preferences.json"))

    def store(
        self,
        user_text: str,
        robot_text: str,
        user_label: str = "User",
        assistant_label: str = "Assistant",
    ) -> None:
        # Episodic storage disabled: user_text is always "[voice input]" (no transcript),
        # making semantic search useless. Re-enable once transcription is available.
        pass

    def build_context(self, query: str) -> str:
        """Return the memory block to append to the system prompt."""
        parts = []

        profile_items = [(k, v) for k, v in self.profile.items() if k != "robot_name"]
        if profile_items:
            lines = "\n".join(f"- {k}: {v}" for k, v in profile_items)
            parts.append(f"Profile:\n{lines}")

        pref_items = self.preferences.items()
        if pref_items:
            lines = "\n".join(f"- {k}: {v}" for k, v in pref_items)
            parts.append(f"Preferences:\n{lines}")

        # Episodic search disabled until real transcripts are available.
        # episodes = self.episodic.search(query, top_k=3)

        return "\n\n".join(parts)

    def process_annotations(self, text: str) -> str:
        """Extract [MEMORY ...] tags, persist all key-value pairs, return clean text."""
        for block in _MEMORY_BLOCK_RE.finditer(text):
            raw = block.group(0)
            type_match = _STORE_TYPE_RE.match(raw)
            if not type_match:
                continue
            store_type = type_match.group(1)
            for key, value in _KV_RE.findall(raw):
                if store_type == "profile":
                    self.profile.set(key, value)
                    logger.info(f"[Memory] Profile updated: {key}={value}")
                else:
                    self.preferences.set(key, value)
                    logger.info(f"[Memory] Preference updated: {key}={value}")
        return strip_annotations(text)
