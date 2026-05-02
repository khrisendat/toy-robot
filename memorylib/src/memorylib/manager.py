import os
from typing import Optional

from .episodic import EpisodicStore
from .face import FaceStore
from .graph import GraphStore
from .media import MediaStore
from .speaker import SpeakerStore


class MemoryManager:
    """
    General-purpose memory manager.

    Owns four sub-stores:
      graph     — entity graph (KuzuDB)
      episodic  — conversation turns with semantic search
      media     — audio and image files
      speaker   — voice profiles for speaker identification (optional)

    If speaker is provided, save_audio() automatically identifies and tags
    recordings with the speaker name unless one is supplied explicitly.
    """

    def __init__(self, base_dir: str):
        base = os.path.abspath(base_dir)
        os.makedirs(base, exist_ok=True)
        self.graph = GraphStore(os.path.join(base, "graph.db"))
        self.episodic = EpisodicStore(os.path.join(base, "episodic.jsonl"))
        self.media = MediaStore(os.path.join(base, "recordings"))
        speaker_path = os.path.join(base, "speakers.jsonl")
        self.speaker = SpeakerStore(path=speaker_path) if SpeakerStore.profiles_exist(speaker_path) else None
        face_path = os.path.join(base, "faces.jsonl")
        self.face = FaceStore(path=face_path) if FaceStore.profiles_exist(face_path) else None

    # ------------------------------------------------------------------
    # Graph
    # ------------------------------------------------------------------

    def remember(
        self,
        subject: str,
        relation: str,
        obj: str,
        subject_type: str = "entity",
        obj_type: str = "entity",
        props: Optional[dict] = None,
    ) -> None:
        """Assert a fact: (subject) -[relation]-> (obj)."""
        self.graph.upsert_entity(subject, subject_type)
        self.graph.upsert_entity(obj, obj_type)
        self.graph.upsert_relation(subject, relation, obj, props)

    def recall(
        self,
        subject: str,
        relation: Optional[str] = None,
        direction: str = "out",
    ) -> list:
        """Return graph neighbors of subject. Each row: [name, type, rel, props]."""
        return self.graph.get_neighbors(subject, rel_type=relation, direction=direction)

    def build_context(self, subject: str, query: str = "") -> str:
        """Return a plain-text facts block for use in a system prompt."""
        rows = self.graph.get_neighbors(subject)
        parts = []
        if rows:
            fact_lines = "\n".join(f"- {row[2]}: {row[0]}" for row in rows)
            parts.append(f"Facts about {subject}:\n{fact_lines}")
        if query:
            episodes = self.episodic.search(query, top_k=3)
            if episodes:
                ep_lines = "\n".join(f"- {e}" for e in episodes)
                parts.append(f"Relevant past exchanges:\n{ep_lines}")
        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Episodic
    # ------------------------------------------------------------------

    def record_exchange(
        self,
        user_text: str,
        assistant_text: str,
        user_label: str = "User",
        assistant_label: str = "Assistant",
        metadata: Optional[dict] = None,
    ) -> None:
        """Embed and persist a conversation turn."""
        text = f"{user_label}: {user_text} {assistant_label}: {assistant_text}"
        self.episodic.store(text, metadata)

    def search_episodes(self, query: str, top_k: int = 3) -> list[str]:
        return self.episodic.search(query, top_k)

    # ------------------------------------------------------------------
    # Media
    # ------------------------------------------------------------------

    def save_audio(self, wav_bytes: bytes, **tags) -> str:
        if self.speaker is not None and "speaker_name" not in tags:
            name = self.speaker.identify(wav_bytes)
            if name:
                tags["speaker_name"] = name
        return self.media.save_audio(wav_bytes, **tags)

    def save_image(self, jpeg_bytes: bytes, **tags) -> str:
        if self.face is not None and "face_name" not in tags:
            name = self.face.identify(jpeg_bytes)
            if name:
                tags["face_name"] = name
        return self.media.save_image(jpeg_bytes, **tags)
