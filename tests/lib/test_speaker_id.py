import io
import wave

import numpy as np
import pytest

from src.lib.speaker_id import SpeakerIdentifier, _wav_to_array

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wav(frequency: float = 440.0, duration: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generate a simple sine-wave WAV so tests don't need real voice audio."""
    n = int(sample_rate * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    samples = (np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples.tobytes())
    return buf.getvalue()


def _fake_embed(wav_bytes: bytes) -> np.ndarray:
    """Deterministic fake embedding based on audio content — no model needed."""
    samples, _ = _wav_to_array(wav_bytes)
    rng = np.random.default_rng(seed=int(abs(samples.mean()) * 1e6) % (2**31))
    vec = rng.standard_normal(256).astype(np.float32)
    return vec / np.linalg.norm(vec)


@pytest.fixture
def sid(tmp_path, monkeypatch):
    """SpeakerIdentifier with _embed replaced by a deterministic fake."""
    s = SpeakerIdentifier(path=str(tmp_path / "speakers.json"))
    monkeypatch.setattr(s, "_embed", _fake_embed)
    return s


# ---------------------------------------------------------------------------
# _wav_to_array
# ---------------------------------------------------------------------------

def test_wav_to_array_shape():
    wav = _make_wav(duration=0.5)
    samples, sr = _wav_to_array(wav)
    assert sr == 16000
    assert len(samples) == 8000
    assert samples.dtype == np.float32


def test_wav_to_array_normalized():
    wav = _make_wav()
    samples, _ = _wav_to_array(wav)
    assert samples.max() <= 1.0
    assert samples.min() >= -1.0


# ---------------------------------------------------------------------------
# Enroll
# ---------------------------------------------------------------------------

class TestEnroll:
    def test_first_enroll_returns_one(self, sid):
        count = sid.enroll("Kabir", _make_wav(440))
        assert count == 1

    def test_second_enroll_increments(self, sid):
        sid.enroll("Kabir", _make_wav(440))
        count = sid.enroll("Kabir", _make_wav(450))
        assert count == 2

    def test_enroll_different_speakers(self, sid):
        sid.enroll("Kabir", _make_wav(440))
        sid.enroll("Dada", _make_wav(880))
        assert set(sid.speakers()) == {"Kabir", "Dada"}

    def test_enroll_persists_to_disk(self, tmp_path, monkeypatch):
        path = str(tmp_path / "speakers.json")
        s1 = SpeakerIdentifier(path=path)
        monkeypatch.setattr(s1, "_embed", _fake_embed)
        s1.enroll("Kabir", _make_wav(440))

        s2 = SpeakerIdentifier(path=path)
        monkeypatch.setattr(s2, "_embed", _fake_embed)
        assert "Kabir" in s2.speakers()
        assert s2.sample_count("Kabir") == 1

    def test_sample_count(self, sid):
        assert sid.sample_count("Kabir") == 0
        sid.enroll("Kabir", _make_wav(440))
        assert sid.sample_count("Kabir") == 1


# ---------------------------------------------------------------------------
# Identify
# ---------------------------------------------------------------------------

class TestIdentify:
    def test_identify_returns_none_with_no_profiles(self, sid):
        assert sid.identify(_make_wav(440)) is None

    def test_identifies_enrolled_speaker(self, sid):
        wav = _make_wav(440)
        sid.enroll("Kabir", wav)
        # Same audio → same embedding → cosine similarity = 1.0
        assert sid.identify(wav) == "Kabir"

    def test_unknown_speaker_returns_none(self, sid, monkeypatch):
        sid.enroll("Kabir", _make_wav(440))
        # Distinct random embedding always below threshold
        monkeypatch.setattr(
            sid, "_embed",
            lambda _: np.array(np.random.default_rng(99).standard_normal(256), dtype=np.float32)
        )
        result = sid.identify(_make_wav(880), threshold=0.99)
        assert result is None

    def test_selects_best_match_among_multiple_speakers(self, sid, monkeypatch):
        wav_a = _make_wav(440)
        wav_b = _make_wav(880)
        sid.enroll("Kabir", wav_a)
        sid.enroll("Dada", wav_b)
        # Identify with Kabir's audio → should match Kabir
        assert sid.identify(wav_a) == "Kabir"

    def test_threshold_respected(self, sid):
        wav = _make_wav(440)
        sid.enroll("Kabir", wav)
        # Threshold above max possible score → None
        assert sid.identify(wav, threshold=1.1) is None


# ---------------------------------------------------------------------------
# profiles_exist
# ---------------------------------------------------------------------------

def test_profiles_exist_false_when_no_file(tmp_path):
    assert not SpeakerIdentifier.profiles_exist(str(tmp_path / "missing.json"))


def test_profiles_exist_true_after_enroll(tmp_path, monkeypatch):
    path = str(tmp_path / "speakers.json")
    s = SpeakerIdentifier(path=path)
    monkeypatch.setattr(s, "_embed", _fake_embed)
    s.enroll("Kabir", _make_wav(440))
    assert SpeakerIdentifier.profiles_exist(path)
