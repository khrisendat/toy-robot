import io
import logging
import os
import subprocess
import tempfile

import numpy as np

logger = logging.getLogger(__name__)

_MODEL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "models")
)
_ONNX = os.path.join(_MODEL_DIR, "kokoro-v1.0.onnx")
_VOICES = os.path.join(_MODEL_DIR, "voices-v1.0.bin")

DEFAULT_VOICE = "bm_daniel"


class KokoroSpeaker:
    """
    TTS speaker backed by the Kokoro ONNX model.

    Drops in as a replacement for MacOSSpeaker — same say() / synthesize() API.
    The model is lazy-loaded on first use.
    """

    def __init__(self, voice: str = DEFAULT_VOICE, speed: float = 1.0):
        self.voice = voice
        self.speed = speed
        self._kokoro = None

    def say(self, text: str) -> None:
        logger.info(f"Speaking: {text}")
        wav_bytes = self.synthesize(text)
        tmp = tempfile.mktemp(suffix=".wav")
        try:
            with open(tmp, "wb") as f:
                f.write(wav_bytes)
            subprocess.run(["afplay", tmp], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Playback error: {e}")
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def synthesize(self, text: str) -> bytes:
        """Return WAV bytes for the given text."""
        kokoro = self._ensure_model()
        samples, sample_rate = kokoro.create(text, voice=self.voice, speed=self.speed)
        return _pcm_to_wav(samples, sample_rate)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ensure_model(self):
        if self._kokoro is None:
            logger.info("[Kokoro] Loading TTS model...")
            from kokoro_onnx import Kokoro
            self._kokoro = Kokoro(_ONNX, _VOICES)
            logger.info("[Kokoro] Model ready.")
        return self._kokoro


def _pcm_to_wav(samples: np.ndarray, sample_rate: int) -> bytes:
    import wave
    pcm = (samples * 32767).astype(np.int16).tobytes()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()
