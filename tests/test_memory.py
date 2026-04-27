import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_fake_model():
    """
    Returns a mock SentenceTransformer whose encode() returns unit vectors
    based on keywords in the text, giving us deterministic cosine similarity
    for ranking tests.

    Keyword → dimension:
      "truck"    → dim 0
      "dinosaur" → dim 1
      "color"    → dim 2
      (other)    → dim 3
    """
    model = MagicMock()

    def encode(text, normalize_embeddings=True):
        vec = np.zeros(4, dtype=np.float32)
        text_lower = text.lower()
        if "truck" in text_lower:
            vec[0] = 1.0
        elif "dinosaur" in text_lower:
            vec[1] = 1.0
        elif "color" in text_lower:
            vec[2] = 1.0
        else:
            vec[3] = 1.0
        return vec

    model.encode.side_effect = encode
    return model


@pytest.fixture
def store(tmp_path):
    """A MemoryStore backed by a temp file, with the real model mocked out."""
    fake_model = make_fake_model()
    with patch("sentence_transformers.SentenceTransformer", return_value=fake_model):
        from src.lib.memory import MemoryStore
        yield MemoryStore(path=str(tmp_path / "memory.json"))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSearch:
    def test_empty_store_returns_empty_list(self, store):
        assert store.search("trucks") == []

    def test_returns_stored_text(self, store):
        store.store("I like trucks", "Me too!")
        results = store.search("trucks")
        assert len(results) == 1
        assert "I like trucks" in results[0]
        assert "Me too!" in results[0]

    def test_top_k_limits_results(self, store):
        store.store("I like trucks", "Cool!")
        store.store("I like dinosaurs", "Roar!")
        store.store("What is your favorite color", "Blue!")
        results = store.search("trucks", top_k=2)
        assert len(results) == 2

    def test_top_k_larger_than_entries_returns_all(self, store):
        store.store("I like trucks", "Cool!")
        results = store.search("trucks", top_k=10)
        assert len(results) == 1

    def test_ranks_most_similar_first(self, store):
        store.store("I like trucks", "Me too!")       # dim 0
        store.store("I like dinosaurs", "Roar!")      # dim 1
        # Query "trucks" → dim 0 → cosine sim 1.0 with truck entry, 0.0 with dinosaur
        results = store.search("trucks", top_k=2)
        assert "trucks" in results[0].lower()
        assert "dinosaurs" in results[1].lower()


class TestStore:
    def test_formats_text_with_default_labels(self, store):
        store.store("I like trucks", "Me too!")
        assert store._entries[0]["text"] == "User: I like trucks Assistant: Me too!"

    def test_formats_text_with_custom_labels(self, store):
        store.store("I like trucks", "Me too!", user_label="Child", assistant_label="Robot")
        assert store._entries[0]["text"] == "Child: I like trucks Robot: Me too!"

    def test_appends_entry(self, store):
        store.store("I like trucks", "Cool!")
        store.store("I like dinosaurs", "Roar!")
        assert len(store._entries) == 2

    def test_entry_has_required_fields(self, store):
        store.store("I like trucks", "Cool!")
        entry = store._entries[0]
        assert "id" in entry
        assert "text" in entry
        assert "embedding" in entry
        assert isinstance(entry["embedding"], list)

    def test_persists_to_disk(self, store, tmp_path):
        store.store("I like trucks", "Cool!")
        memory_file = tmp_path / "memory.json"
        assert memory_file.exists()
        lines = [json.loads(line) for line in memory_file.read_text().splitlines() if line.strip()]
        assert len(lines) == 1

    def test_rebuilds_matrix_after_store(self, store):
        assert store._matrix is None
        store.store("I like trucks", "Cool!")
        assert store._matrix is not None
        assert store._matrix.shape == (1, 4)


class TestPersistence:
    def test_reloads_entries_from_disk(self, tmp_path):
        fake_model = make_fake_model()
        path = str(tmp_path / "memory.json")
        with patch("sentence_transformers.SentenceTransformer", return_value=fake_model):
            from src.lib.memory import MemoryStore
            s1 = MemoryStore(path=path)
            s1.store("I like trucks", "Me too!")

            s2 = MemoryStore(path=path)
            assert len(s2._entries) == 1
            assert s2._matrix is not None

    def test_starts_fresh_when_no_file(self, store):
        assert store._entries == []
        assert store._matrix is None

    def test_handles_corrupt_file(self, tmp_path):
        memory_file = tmp_path / "memory.json"
        memory_file.write_text("not valid json{{{")
        fake_model = make_fake_model()
        with patch("sentence_transformers.SentenceTransformer", return_value=fake_model):
            from src.lib.memory import MemoryStore
            s = MemoryStore(path=str(memory_file))
            assert s._entries == []
            assert s._matrix is None
