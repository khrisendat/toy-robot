import io
import json

import numpy as np
import pytest

from memorylib import FaceStore
from memorylib.face import _jpeg_to_array


def _make_jpeg(color=(128, 64, 32)) -> bytes:
    """Minimal valid JPEG bytes via PIL (no real face content needed for stub tests)."""
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), color).save(buf, format="JPEG")
    return buf.getvalue()


def _fake_encode(jpeg_bytes: bytes) -> list:
    """Deterministic 128-dim unit vector based on pixel content — no model needed."""
    arr = _jpeg_to_array(jpeg_bytes).flatten().astype(np.float32)
    seed = int(abs(arr.mean()) * 1e6) % (2**31)
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(128).astype(np.float64)
    return [v / np.linalg.norm(v)]


@pytest.fixture
def store(tmp_path, monkeypatch):
    s = FaceStore(path=str(tmp_path / "faces.jsonl"))
    monkeypatch.setattr(s, "_encode", _fake_encode)
    return s


class TestEnroll:
    def test_first_enroll_returns_one(self, store):
        assert store.enroll("Kabir", _make_jpeg()) == 1

    def test_second_enroll_increments(self, store):
        store.enroll("Kabir", _make_jpeg((100, 100, 100)))
        assert store.enroll("Kabir", _make_jpeg((101, 101, 101))) == 2

    def test_enroll_different_people(self, store):
        store.enroll("Kabir", _make_jpeg((10, 20, 30)))
        store.enroll("Dada", _make_jpeg((40, 50, 60)))
        assert set(store.faces()) == {"Kabir", "Dada"}

    def test_no_face_detected_returns_existing_count(self, store, monkeypatch):
        monkeypatch.setattr(store, "_encode", lambda _: [])
        assert store.enroll("Kabir", _make_jpeg()) == 0

    def test_enroll_persists_to_disk(self, tmp_path, monkeypatch):
        path = str(tmp_path / "faces.jsonl")
        s1 = FaceStore(path=path)
        monkeypatch.setattr(s1, "_encode", _fake_encode)
        s1.enroll("Kabir", _make_jpeg())

        s2 = FaceStore(path=path)
        assert "Kabir" in s2.faces()
        assert s2.sample_count("Kabir") == 1

    def test_jsonl_format(self, store, tmp_path):
        store.enroll("Kabir", _make_jpeg())
        line = (tmp_path / "faces.jsonl").read_text().strip()
        entry = json.loads(line)
        assert entry["name"] == "Kabir"
        assert isinstance(entry["encoding"], list)
        assert len(entry["encoding"]) == 128

    def test_sample_count(self, store):
        assert store.sample_count("Kabir") == 0
        store.enroll("Kabir", _make_jpeg())
        assert store.sample_count("Kabir") == 1


class TestIdentify:
    def test_returns_none_with_no_profiles(self, store):
        assert store.identify(_make_jpeg()) is None

    def test_identifies_enrolled_person(self, store):
        img = _make_jpeg()
        store.enroll("Kabir", img)
        assert store.identify(img) == "Kabir"

    def test_unknown_face_returns_none(self, store, monkeypatch):
        store.enroll("Kabir", _make_jpeg((10, 20, 30)))
        # Return a random encoding far from anything enrolled
        rng = np.random.default_rng(99)
        v = rng.standard_normal(128).astype(np.float64)
        v = v / np.linalg.norm(v)
        monkeypatch.setattr(store, "_encode", lambda _: [v])
        assert store.identify(_make_jpeg(), threshold=0.1) is None

    def test_no_face_in_image_returns_none(self, store, monkeypatch):
        store.enroll("Kabir", _make_jpeg())
        monkeypatch.setattr(store, "_encode", lambda _: [])
        assert store.identify(_make_jpeg()) is None

    def test_selects_closest_match(self, store, monkeypatch):
        img_a = _make_jpeg((10, 20, 30))
        img_b = _make_jpeg((200, 210, 220))
        store.enroll("Kabir", img_a)
        store.enroll("Dada", img_b)
        assert store.identify(img_a) == "Kabir"

    def test_threshold_respected(self, store):
        img = _make_jpeg()
        store.enroll("Kabir", img)
        assert store.identify(img, threshold=0.0) is None


class TestProfilesExist:
    def test_false_when_no_file(self, tmp_path):
        assert not FaceStore.profiles_exist(str(tmp_path / "missing.jsonl"))

    def test_true_after_enroll(self, tmp_path, monkeypatch):
        path = str(tmp_path / "faces.jsonl")
        s = FaceStore(path=path)
        monkeypatch.setattr(s, "_encode", _fake_encode)
        s.enroll("Kabir", _make_jpeg())
        assert FaceStore.profiles_exist(path)
