import json

import numpy as np
import pytest

from memorylib import EpisodicStore


@pytest.fixture
def store(tmp_path, monkeypatch):
    """EpisodicStore with a deterministic stub model (no real sentence-transformers)."""
    s = EpisodicStore(path=str(tmp_path / "episodic.jsonl"))

    class _StubModel:
        def encode(self, text, normalize_embeddings=False):
            # Deterministic: hash text to a stable unit vector.
            seed = sum(ord(c) for c in text) % 256
            rng = np.random.default_rng(seed)
            v = rng.standard_normal(16).astype(np.float32)
            return v / np.linalg.norm(v)

    s._model = _StubModel()
    return s


class TestStore:
    def test_store_adds_entry(self, store):
        store.store("hello world")
        assert len(store) == 1

    def test_store_persists_to_disk(self, store, tmp_path):
        store.store("hello world")
        path = tmp_path / "episodic.jsonl"
        assert path.exists()
        with open(path) as f:
            entry = json.loads(f.readline())
        assert entry["text"] == "hello world"
        assert "embedding" in entry

    def test_store_with_metadata(self, store, tmp_path):
        store.store("hi", metadata={"speaker": "Kabir"})
        with open(tmp_path / "episodic.jsonl") as f:
            entry = json.loads(f.readline())
        assert entry["metadata"] == {"speaker": "Kabir"}

    def test_multiple_entries(self, store):
        store.store("first")
        store.store("second")
        assert len(store) == 2


class TestSearch:
    def test_search_empty_returns_empty(self, store):
        assert store.search("anything") == []

    def test_search_returns_strings(self, store):
        store.store("I like cats")
        results = store.search("cats", top_k=1)
        assert len(results) == 1
        assert isinstance(results[0], str)

    def test_search_respects_top_k(self, store):
        for i in range(5):
            store.store(f"entry {i}")
        results = store.search("entry", top_k=3)
        assert len(results) == 3

    def test_search_top_k_larger_than_entries(self, store):
        store.store("only one")
        results = store.search("one", top_k=10)
        assert len(results) == 1


class TestPersistence:
    def test_reloads_indexed_entries(self, tmp_path):
        path = str(tmp_path / "episodic.jsonl")

        s1 = EpisodicStore(path=path)

        class _StubModel:
            def encode(self, text, normalize_embeddings=False):
                seed = sum(ord(c) for c in text) % 256
                rng = np.random.default_rng(seed)
                v = rng.standard_normal(16).astype(np.float32)
                return v / np.linalg.norm(v)

        s1._model = _StubModel()
        s1.store("remembered fact")

        s2 = EpisodicStore(path=path)
        assert len(s2) == 1
        assert s2._matrix is not None
