import json

import pytest

from memorylib import MediaStore


@pytest.fixture
def store(tmp_path):
    return MediaStore(base_dir=str(tmp_path / "recordings"))


class TestSaveAudio:
    def test_returns_path(self, store):
        path = store.save_audio(b"RIFF...")
        assert path.endswith(".wav")

    def test_file_written(self, store):
        import os
        path = store.save_audio(b"RIFF...")
        assert os.path.exists(path)
        with open(path, "rb") as f:
            assert f.read() == b"RIFF..."

    def test_tags_in_log(self, store, tmp_path):
        store.save_audio(b"data", speaker_name="Kabir")
        log = tmp_path / "recordings" / "log.jsonl"
        entry = json.loads(log.read_text().strip())
        assert entry["speaker_name"] == "Kabir"
        assert entry["type"] == "audio"

    def test_log_has_timestamp(self, store, tmp_path):
        store.save_audio(b"data")
        log = tmp_path / "recordings" / "log.jsonl"
        entry = json.loads(log.read_text().strip())
        assert "timestamp" in entry


class TestSaveImage:
    def test_returns_jpg_path(self, store):
        path = store.save_image(b"\xff\xd8\xff")
        assert path.endswith(".jpg")

    def test_file_written(self, store):
        import os
        path = store.save_image(b"\xff\xd8\xff")
        assert os.path.exists(path)

    def test_log_entry_type_image(self, store, tmp_path):
        store.save_image(b"\xff\xd8\xff")
        log = tmp_path / "recordings" / "log.jsonl"
        entry = json.loads(log.read_text().strip())
        assert entry["type"] == "image"


class TestMultipleWrites:
    def test_log_has_one_line_per_save(self, store, tmp_path):
        store.save_audio(b"a")
        store.save_audio(b"b")
        store.save_image(b"c")
        log = tmp_path / "recordings" / "log.jsonl"
        lines = [line for line in log.read_text().splitlines() if line.strip()]
        assert len(lines) == 3
