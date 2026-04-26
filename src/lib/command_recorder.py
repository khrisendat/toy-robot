import io
import wave
from typing import List, Optional

import webrtcvad

_RATE = 16000
_FRAME_SAMPLES = 480          # 30 ms @ 16 kHz
_FRAME_BYTES = _FRAME_SAMPLES * 2
_MIN_SPEECH_FRAMES = 7        # ~200 ms to confirm speech started
_TRAILING_SILENCE_FRAMES = 33  # ~1 s of silence ends the utterance
_MAX_COMMAND_FRAMES = 267     # ~8 s hard cap


class CommandRecorder:
    """Buffers streamed PCM and signals when an utterance is complete.

    Feed raw int16 mono 16 kHz PCM via feed(). Returns WAV bytes once:
    - at least MIN_SPEECH_FRAMES of speech were detected, AND
    - TRAILING_SILENCE_FRAMES of silence follow, OR
    - MAX_COMMAND_FRAMES total frames have been received (hard cap).
    """

    def __init__(self):
        self._vad = webrtcvad.Vad(2)
        self._pending = b""
        self._frames: List[bytes] = []
        self._speech_started = False
        self._speech_count = 0
        self._silence_count = 0

    def feed(self, pcm: bytes) -> Optional[bytes]:
        """Feed raw PCM bytes. Returns WAV bytes when utterance is complete, else None."""
        self._pending += pcm
        while len(self._pending) >= _FRAME_BYTES:
            frame, self._pending = (
                self._pending[:_FRAME_BYTES],
                self._pending[_FRAME_BYTES:],
            )
            self._frames.append(frame)
            if len(self._frames) >= _MAX_COMMAND_FRAMES:
                return self._to_wav()
            is_speech = self._vad.is_speech(frame, _RATE)
            if is_speech:
                self._speech_started = True
                self._speech_count += 1
                self._silence_count = 0
            elif self._speech_started:
                self._silence_count += 1
                if (
                    self._silence_count >= _TRAILING_SILENCE_FRAMES
                    and self._speech_count >= _MIN_SPEECH_FRAMES
                ):
                    return self._to_wav()
        return None

    def _to_wav(self) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(_RATE)
            wf.writeframes(b"".join(self._frames))
        return buf.getvalue()
