"""
Phase 2 tests: validate CommandRecorder VAD-based recording boundaries.

Three termination conditions are tested:
  1. Trailing silence after sufficient speech  →  normal utterance end
  2. Hard cap (MAX_COMMAND_FRAMES)             →  safety net for continuous speech
  3. Silence only                              →  no false trigger

Speech PCM comes from the same real-audio samples used by the wake-word
tests so webrtcvad sees realistic frequency content.

Run:  pytest tests/lib/test_command_recorder.py -v
"""

import io
import os
import wave

from src.lib.command_recorder import (
    _FRAME_BYTES,
    _MAX_COMMAND_FRAMES,
    CommandRecorder,
)

SAMPLES = os.path.join(os.path.dirname(__file__), "..", "hardware", "samples")
CHUNK_BYTES = 2730  # browser-sized chunks: 1365 int16 samples


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_pcm(filename: str) -> bytes:
    with wave.open(os.path.join(SAMPLES, filename), "rb") as wf:
        return wf.readframes(wf.getnframes())


def _silence(seconds: float) -> bytes:
    return b"\x00\x00" * int(16000 * seconds)


def _loop_pcm(pcm: bytes, target_bytes: int) -> bytes:
    """Repeat pcm until we have at least target_bytes."""
    result = b""
    while len(result) < target_bytes:
        result += pcm
    return result[:target_bytes]


def _feed(recorder: CommandRecorder, pcm: bytes, chunk: int = CHUNK_BYTES):
    """Feed PCM in chunks. Returns the first non-None result, or None if never triggered."""
    for offset in range(0, len(pcm), chunk):
        result = recorder.feed(pcm[offset : offset + chunk])
        if result is not None:
            return result
    return None


def _parse_wav(data: bytes):
    with wave.open(io.BytesIO(data), "rb") as wf:
        return wf.getframerate(), wf.getnchannels(), wf.getsampwidth(), wf.getnframes()


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_silence_never_triggers_before_cap():
    """5 seconds of silence (well under the 8 s cap) should produce nothing."""
    result = _feed(CommandRecorder(), _silence(5))
    assert result is None


def test_speech_then_silence_triggers():
    """Real speech followed by 2 s of silence should complete the recording."""
    speech = _load_pcm("what_time_is_it.wav")
    pcm = speech + _silence(2)
    result = _feed(CommandRecorder(), pcm)
    assert result is not None, "Expected WAV after speech + silence, got None"


def test_hard_cap_triggers():
    """Continuous speech past the 8 s cap should be returned at the cap."""
    # Need slightly more than MAX_COMMAND_FRAMES frames worth of data.
    target = (_MAX_COMMAND_FRAMES + 5) * _FRAME_BYTES
    speech = _loop_pcm(_load_pcm("what_time_is_it.wav"), target)
    result = _feed(CommandRecorder(), speech)
    assert result is not None, "Expected WAV at hard cap, got None"


def test_output_is_valid_wav():
    """The returned bytes must be a valid 16 kHz mono 16-bit WAV."""
    speech = _load_pcm("what_time_is_it.wav")
    result = _feed(CommandRecorder(), speech + _silence(2))
    assert result is not None
    rate, channels, width, _ = _parse_wav(result)
    assert rate == 16000
    assert channels == 1
    assert width == 2


def test_output_contains_speech_frames():
    """The returned WAV should contain at least as many frames as the speech input."""
    speech = _load_pcm("what_time_is_it.wav")
    result = _feed(CommandRecorder(), speech + _silence(2))
    assert result is not None
    _, _, _, frames = _parse_wav(result)
    speech_frames = len(speech) // 2  # int16 samples
    assert frames >= speech_frames


def test_non_aligned_chunk_sizes_produce_same_result():
    """Feeding in odd-sized chunks should produce the same outcome as standard chunks."""
    pcm = _load_pcm("what_time_is_it.wav") + _silence(2)
    result_standard = _feed(CommandRecorder(), pcm, chunk=CHUNK_BYTES)
    result_odd      = _feed(CommandRecorder(), pcm, chunk=997)
    assert (result_standard is None) == (result_odd is None)
