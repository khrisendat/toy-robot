import io
import logging
import wave

import numpy as np
import pyaudio
import webrtcvad

from src import config

logger = logging.getLogger(__name__)

RATE = 16000
# 480 samples = exactly 30ms at 16000Hz — required by webrtcvad
CHUNK = 480
CHUNKS_PER_SECOND = RATE // CHUNK                  # ~33 chunks/sec
VAD_AGGRESSIVENESS = 2                              # 0 (permissive) – 3 (strict)
MIN_SPEECH_CHUNKS = CHUNKS_PER_SECOND // 5         # ~200ms of speech to confirm start
TRAILING_SILENCE_CHUNKS = CHUNKS_PER_SECOND        # ~1s of silence to stop


class Listener:
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)

    def listen(self, duration=8):
        logger.info("Listening for command...")

        stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=2,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            input_device_index=config.AUDIO_INPUT_DEVICE_INDEX,
        )

        frames = []
        total_chunks = CHUNKS_PER_SECOND * duration
        speech_started = False
        speech_chunks = 0
        trailing_silent_chunks = 0

        for _ in range(total_chunks):
            data = stream.read(CHUNK, exception_on_overflow=False)
            mono = self._stereo_to_mono(data)
            frames.append(mono)

            is_speech = self.vad.is_speech(mono, RATE)

            if is_speech:
                speech_started = True
                speech_chunks += 1
                trailing_silent_chunks = 0
            elif speech_started:
                trailing_silent_chunks += 1
                if trailing_silent_chunks >= TRAILING_SILENCE_CHUNKS and speech_chunks >= MIN_SPEECH_CHUNKS:
                    logger.debug("Silence detected after speech, stopping early.")
                    break

        stream.stop_stream()
        stream.close()

        if not speech_started:
            logger.info("No speech detected (silence)")
            return None

        elapsed = len(frames) / CHUNKS_PER_SECOND
        logger.info(f"Finished recording ({elapsed:.1f}s).")
        return self._to_wav(frames)

    def _stereo_to_mono(self, stereo_data):
        audio = np.frombuffer(stereo_data, dtype=np.int16).reshape(-1, 2)
        return np.mean(audio, axis=1).astype(np.int16).tobytes()

    def _to_wav(self, frames):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(RATE)
            wf.writeframes(b"".join(frames))
        return buf.getvalue()

    def __del__(self):
        if self.pa is not None:
            self.pa.terminate()
