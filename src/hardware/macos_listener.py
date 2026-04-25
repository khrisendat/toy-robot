import io
import logging
import wave

import pyaudio
import webrtcvad

logger = logging.getLogger(__name__)

NATIVE_RATE = 48000
TARGET_RATE = 16000
# 960 samples = exactly 20ms at 48000Hz — required by webrtcvad
CHUNK = 960
CHUNKS_PER_SECOND = NATIVE_RATE // CHUNK           # 50 chunks/sec
VAD_AGGRESSIVENESS = 2                              # 0 (permissive) – 3 (strict)
MIN_SPEECH_CHUNKS = CHUNKS_PER_SECOND // 5         # 200ms of speech to confirm start
TRAILING_SILENCE_CHUNKS = CHUNKS_PER_SECOND        # 1s of silence to stop


class MacOSListener:
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)

    def listen(self, duration=8):
        logger.info("Listening for command...")

        stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=NATIVE_RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )

        frames = []
        total_chunks = CHUNKS_PER_SECOND * duration
        speech_started = False
        speech_chunks = 0
        trailing_silent_chunks = 0

        for _ in range(total_chunks):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)

            is_speech = self.vad.is_speech(data, NATIVE_RATE)

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

    def _downsample(self, frames):
        import numpy as np
        audio = np.frombuffer(b"".join(frames), dtype=np.int16).astype(np.float32)
        ratio = TARGET_RATE / NATIVE_RATE
        target_len = int(len(audio) * ratio)
        indices = np.linspace(0, len(audio) - 1, target_len)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.int16).tobytes()

    def _to_wav(self, frames):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(TARGET_RATE)
            wf.writeframes(self._downsample(frames))
        return buf.getvalue()

    def __del__(self):
        if self.pa is not None:
            self.pa.terminate()
