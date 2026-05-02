import numpy as np
import pytest

from memorylib import MemoryManager


@pytest.fixture
def mgr(tmp_path):
    m = MemoryManager(base_dir=str(tmp_path))

    class _StubModel:
        def encode(self, text, normalize_embeddings=False):
            seed = sum(ord(c) for c in text) % 256
            rng = np.random.default_rng(seed)
            v = rng.standard_normal(16).astype(np.float32)
            return v / np.linalg.norm(v)

    m.episodic._model = _StubModel()
    return m


class TestRememberRecall:
    def test_remember_creates_triple(self, mgr):
        mgr.remember("Alice", "likes", "cats")
        rows = mgr.recall("Alice", relation="likes")
        assert len(rows) == 1
        assert rows[0][0] == "cats"

    def test_recall_all_relations(self, mgr):
        mgr.remember("Alice", "likes", "cats")
        mgr.remember("Alice", "dislikes", "rain")
        rows = mgr.recall("Alice")
        names = {r[0] for r in rows}
        assert names == {"cats", "rain"}

    def test_recall_empty(self, mgr):
        mgr.graph.upsert_entity("Ghost", "entity")
        assert mgr.recall("Ghost") == []


class TestBuildContext:
    def test_returns_empty_for_unknown_subject(self, mgr):
        assert mgr.build_context("Nobody") == ""

    def test_includes_outbound_facts(self, mgr):
        mgr.remember("Alice", "likes", "cats")
        ctx = mgr.build_context("Alice")
        assert "Facts about Alice" in ctx
        assert "likes: cats" in ctx

    def test_includes_episodic_when_query_given(self, mgr):
        mgr.record_exchange("I love cats", "Cats are great!")
        ctx = mgr.build_context("Alice", query="cats")
        assert "cats" in ctx.lower()


class TestRecordExchange:
    def test_increments_episodic_count(self, mgr):
        assert len(mgr.episodic) == 0
        mgr.record_exchange("hello", "hi there")
        assert len(mgr.episodic) == 1

    def test_search_episodes_returns_result(self, mgr):
        mgr.record_exchange("I like trains", "Trains are cool!")
        results = mgr.search_episodes("trains", top_k=1)
        assert len(results) == 1
        assert "train" in results[0].lower()


class TestMedia:
    def test_save_audio_returns_path(self, mgr):
        path = mgr.save_audio(b"RIFF...")
        assert path.endswith(".wav")

    def test_save_image_returns_path(self, mgr):
        path = mgr.save_image(b"\xff\xd8")
        assert path.endswith(".jpg")

    def test_save_audio_without_speaker_store_no_tag(self, mgr, tmp_path):
        import json
        mgr.save_audio(b"RIFF...")
        log = (tmp_path / "recordings" / "log.jsonl").read_text()
        entry = json.loads(log.strip())
        assert "speaker_name" not in entry


class TestSpeakerIntegration:
    @pytest.fixture
    def mgr_with_speaker(self, tmp_path, monkeypatch):
        (tmp_path / "speakers.jsonl").write_text("{}")  # presence triggers SpeakerStore creation
        m = MemoryManager(base_dir=str(tmp_path))
        monkeypatch.setattr(m.speaker, "identify", lambda wav, **kw: "Kabir")
        return m

    def test_speaker_attribute_set(self, mgr_with_speaker):
        assert mgr_with_speaker.speaker is not None

    def test_no_speakers_json_means_no_speaker_store(self, tmp_path):
        m = MemoryManager(base_dir=str(tmp_path))
        assert m.speaker is None

    def test_save_audio_auto_tags_speaker(self, mgr_with_speaker, tmp_path):
        import json
        mgr_with_speaker.save_audio(b"RIFF...")
        log = (tmp_path / "recordings" / "log.jsonl").read_text()
        entry = json.loads(log.strip())
        assert entry["speaker_name"] == "Kabir"

    def test_explicit_speaker_name_not_overwritten(self, mgr_with_speaker, tmp_path):
        import json
        mgr_with_speaker.save_audio(b"RIFF...", speaker_name="Dada")
        log = (tmp_path / "recordings" / "log.jsonl").read_text()
        entry = json.loads(log.strip())
        assert entry["speaker_name"] == "Dada"

    def test_unknown_speaker_no_tag(self, tmp_path, monkeypatch):
        (tmp_path / "speakers.jsonl").write_text("{}")
        import json
        m = MemoryManager(base_dir=str(tmp_path))
        monkeypatch.setattr(m.speaker, "identify", lambda wav, **kw: None)
        m.save_audio(b"RIFF...")
        log = (tmp_path / "recordings" / "log.jsonl").read_text()
        entry = json.loads(log.strip())
        assert "speaker_name" not in entry
