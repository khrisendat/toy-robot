import logging
from dataclasses import dataclass
from typing import Callable, Optional

from .manager import MemoryManager

logger = logging.getLogger(__name__)

Triple = tuple[str, str, str]  # (subject, relation, object)
Extractor = Callable[[str], list[Triple]]


@dataclass
class ReflectionResult:
    audio_tagged: int = 0    # audio entries that gained a speaker_name
    images_tagged: int = 0   # image entries that gained a face_name
    facts_written: int = 0   # graph triples asserted from episodic mining

    def __str__(self) -> str:
        return (
            f"audio_tagged={self.audio_tagged}, "
            f"images_tagged={self.images_tagged}, "
            f"facts_written={self.facts_written}"
        )


class Reflector:
    """
    Off-line reflection over persisted memory data.

    Two passes are available:

    reidentify_media()
        Scans the media manifest for audio/image entries that were saved
        without a speaker or face tag. Runs the recognisers and rewrites the
        manifest with any newly-identified tags.

    mine_episodic(extractor)
        Iterates over all episodic entries and passes each text to a caller-
        supplied extractor function. The extractor returns a list of
        (subject, relation, object) triples which are asserted in the graph.
        No extractor is bundled — the caller supplies one (LLM, rule-based,
        etc.) keeping this library decoupled from any specific model.

    run(extractor=None) combines both passes.
    """

    def __init__(self, memory: MemoryManager):
        self._memory = memory

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, extractor: Optional[Extractor] = None) -> ReflectionResult:
        result = ReflectionResult()
        result.audio_tagged, result.images_tagged = self.reidentify_media()
        if extractor is not None:
            result.facts_written = self.mine_episodic(extractor)
        return result

    def reidentify_media(self) -> tuple[int, int]:
        """
        Re-run recognisers on untagged media entries.

        Returns (audio_tagged, images_tagged) counts.
        Skips the pass entirely if the relevant recogniser is unavailable.
        """
        entries = self._memory.media.read_log()
        if not entries:
            return 0, 0

        audio_tagged = 0
        images_tagged = 0

        for entry in entries:
            kind = entry.get("type")
            path = entry.get("file", "")

            if kind == "audio" and "speaker_name" not in entry:
                name = self._identify_audio_file(path)
                if name:
                    entry["speaker_name"] = name
                    audio_tagged += 1

            elif kind == "image" and "face_name" not in entry:
                name = self._identify_image_file(path)
                if name:
                    entry["face_name"] = name
                    images_tagged += 1

        if audio_tagged or images_tagged:
            self._memory.media.rewrite_log(entries)
            logger.info(
                f"[Reflect] Re-identified {audio_tagged} audio, {images_tagged} image entries"
            )

        return audio_tagged, images_tagged

    def mine_episodic(self, extractor: Extractor) -> int:
        """
        Extract graph facts from episodic entries using a caller-supplied extractor.

        extractor(text: str) -> list[Triple]
            where Triple = (subject: str, relation: str, object: str)

        Returns the number of triples written to the graph.
        """
        written = 0
        for entry in self._memory.episodic.all_entries():
            text = entry.get("text", "")
            if not text:
                continue
            try:
                triples = extractor(text)
            except Exception as e:
                logger.warning(f"[Reflect] Extractor raised on entry {entry.get('id')}: {e}")
                continue
            for subj, rel, obj in triples:
                self._memory.graph.upsert_entity(subj)
                self._memory.graph.upsert_entity(obj)
                self._memory.graph.upsert_relation(subj, rel, obj)
                written += 1

        if written:
            logger.info(f"[Reflect] Wrote {written} fact(s) from episodic mining")
        return written

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _identify_audio_file(self, path: str) -> Optional[str]:
        if self._memory.speaker is None:
            return None
        try:
            with open(path, "rb") as f:
                wav_bytes = f.read()
            return self._memory.speaker.identify(wav_bytes)
        except Exception as e:
            logger.warning(f"[Reflect] Could not identify audio {path}: {e}")
            return None

    def _identify_image_file(self, path: str) -> Optional[str]:
        if self._memory.face is None:
            return None
        try:
            with open(path, "rb") as f:
                jpeg_bytes = f.read()
            return self._memory.face.identify(jpeg_bytes)
        except Exception as e:
            logger.warning(f"[Reflect] Could not identify image {path}: {e}")
            return None
