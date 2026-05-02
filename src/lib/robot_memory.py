import logging
import os
import re
from datetime import datetime
from typing import Optional

from memorylib import MemoryManager

from .. import config

logger = logging.getLogger(__name__)

_MEMORY_BLOCK_RE = re.compile(r'\[MEMORY\s+[^\]]+\]')
_STORE_TYPE_RE = re.compile(r'\[MEMORY\s+(profile|preference)\s+')
_KV_RE = re.compile(r'([\w_]+)="([^"]+)"')
_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "memory"))

_PET_RELS = {"has_pet", "has_pet_type"}


def strip_annotations(text: str) -> str:
    return _MEMORY_BLOCK_RE.sub("", text).strip()


class RobotMemory(MemoryManager):
    """
    MemoryManager subclass with robot-specific annotation parsing and
    context formatting for the child-robot use case.
    """

    def __init__(self, base_dir: str = _BASE_DIR, user_name: Optional[str] = None):
        super().__init__(base_dir)
        self._user_name = user_name or config.USER_NAME
        self.graph.upsert_entity(self._user_name, "person")
        self.graph.upsert_entity("Robot", "robot")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_robot_name(self) -> Optional[str]:
        rows = self.graph.get_neighbors("Robot", rel_type="named")
        return rows[0][0] if rows else None

    def build_context(self, query: str = "") -> str:  # type: ignore[override]
        user = self._user_name
        lines = []

        for row in self.graph.get_neighbors(user, rel_type="parent_of", direction="in"):
            lines.append(f"{row[0].lower()}: yes")
        for row in self.graph.get_neighbors(user, rel_type="sibling_of", direction="in"):
            lines.append(f"sibling: {row[0]}")

        pets = self.graph.get_neighbors(user, rel_type="has_pet")
        for pet_row in pets:
            pet = pet_row[0]
            lines.append(f"pet_name: {pet}")
            for r in self.graph.get_neighbors(pet, rel_type="pet_type"):
                lines.append(f"pet: {r[0]}")
            for r in self.graph.get_neighbors(pet, rel_type="species"):
                lines.append(f"pet_species: {r[0]}")

        if not pets:
            for row in self.graph.get_neighbors(user, rel_type="has_pet_type"):
                lines.append(f"pet: {row[0]}")

        for row in self.graph.get_neighbors(user):
            rel = row[2]
            if rel in _PET_RELS:
                continue
            lines.append(f"{rel}: {row[0]}")

        if not lines:
            return ""

        bullet_list = "\n".join(f"- {line}" for line in lines)
        return f"Facts about {user}:\n{bullet_list}"

    def record_turn(self, user_text: str, robot_text: str, speaker_name: Optional[str] = None) -> None:
        """Record a conversation turn with speaker attribution."""
        metadata = {"speaker": speaker_name} if speaker_name else None
        self.record_exchange(user_text, robot_text, metadata=metadata)
        if speaker_name and speaker_name != self._user_name:
            date = datetime.now().strftime("%Y-%m-%d")
            self.graph.upsert_entity(speaker_name, "person")
            self.graph.upsert_entity(date, "date")
            self.graph.upsert_relation(speaker_name, "last_seen", date)

    def process_annotations(self, text: str) -> str:
        """Extract [MEMORY ...] tags, write to graph, return clean text."""
        for block in _MEMORY_BLOCK_RE.finditer(text):
            raw = block.group(0)
            type_match = _STORE_TYPE_RE.match(raw)
            if not type_match:
                continue
            store_type = type_match.group(1)
            pairs = dict(_KV_RE.findall(raw))
            self._write_to_graph(store_type, pairs)
        return strip_annotations(text)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _write_to_graph(self, store_type: str, pairs: dict) -> None:
        user = self._user_name
        pairs = dict(pairs)

        if store_type == "profile":
            for key, value in pairs.items():
                if key == "called":
                    self.graph.upsert_entity(value, "alias")
                    self.graph.upsert_relation(user, "called", value)
                elif key == "age":
                    self.graph.upsert_entity(value, "value")
                    self.graph.upsert_relation(user, "age", value)
                elif key == "robot_name":
                    self.graph.upsert_entity(value, "robot_name")
                    self.graph.upsert_relation("Robot", "named", value)
                elif key in ("mama", "dada"):
                    name = value if value.lower() != "yes" else key.capitalize()
                    self.graph.upsert_entity(name, "person")
                    self.graph.upsert_relation(name, "parent_of", user)
                elif key == "sibling":
                    self.graph.upsert_entity(value, "person")
                    self.graph.upsert_relation(value, "sibling_of", user)
                else:
                    self.graph.upsert_entity(value, "value")
                    self.graph.upsert_relation(user, key, value)
                logger.info(f"[Memory] Profile fact: {key}={value}")

        else:  # preference
            pet_name = pairs.pop("pet_name", None)
            if pet_name:
                self.graph.upsert_entity(pet_name, "pet")
                self.graph.upsert_relation(user, "has_pet", pet_name)
                if "pet" in pairs:
                    v = pairs.pop("pet")
                    self.graph.upsert_entity(v, "value")
                    self.graph.upsert_relation(pet_name, "pet_type", v)
                if "pet_species" in pairs:
                    v = pairs.pop("pet_species")
                    self.graph.upsert_entity(v, "value")
                    self.graph.upsert_relation(pet_name, "species", v)
            elif "pet" in pairs:
                v = pairs.pop("pet")
                self.graph.upsert_entity(v, "value")
                self.graph.upsert_relation(user, "has_pet_type", v)

            if "pet_species" in pairs:
                v = pairs.pop("pet_species")
                existing = self.graph.get_neighbors(user, rel_type="has_pet")
                target = existing[-1][0] if existing else user
                self.graph.upsert_entity(v, "value")
                self.graph.upsert_relation(target, "species", v)

            for key, value in pairs.items():
                self.graph.upsert_entity(value, "topic")
                self.graph.upsert_relation(user, key, value)
                logger.info(f"[Memory] Preference: {key}={value}")

