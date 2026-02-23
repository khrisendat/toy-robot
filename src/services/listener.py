import io
import logging
import time
import wave
import pyaudio
import numpy as np
from src import config

logger = logging.getLogger(__name__)

SILENCE_RMS_THRESHOLD = 500   # below this RMS level is treated as silence
CHUNKS_PER_SECOND = int(16000 / 1024)        # ~15 chunks/sec
TRAILING_SILENCE_CHUNKS = CHUNKS_PER_SECOND  # stop after ~1s of silence post-speech
MIN_SPEECH_CHUNKS = CHUNKS_PER_SECOND        # must record at least ~1s before silence can stop it

class Listener:
    def __init__(self):
        self.pa = pyaudio.PyAudio()

    def _stereo_to_mono(self, stereo_data):
        """Convert stereo audio data to mono by averaging channels."""
        audio = np.frombuffer(stereo_data, dtype=np.int16)
        audio = audio.reshape(-1, 2)
        mono = np.mean(audio, axis=1).astype(np.int16)
        return mono.tobytes()

    def _to_wav(self, frames):
        """Wrap raw PCM frames in a WAV container."""
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(16000)
            wf.writeframes(b"".join(frames))
        return buf.getvalue()

    def listen(self, duration=5):
        logger.info("Listening for command...")

        stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=2,
            rate=16000,
            input=True,
            frames_per_buffer=1024,
            input_device_index=config.AUDIO_INPUT_DEVICE_INDEX
        )

        frames = []
        total_chunks = int(16000 / 1024 * duration)
        speech_started = False
        speech_chunks = 0
        trailing_silent_chunks = 0

        for i in range(total_chunks):
            data = stream.read(1024)
            mono_data = self._stereo_to_mono(data)
            frames.append(mono_data)

            chunk_array = np.frombuffer(mono_data, dtype=np.int16)
            rms = np.sqrt(np.mean(chunk_array.astype(np.float32) ** 2))

            if rms >= SILENCE_RMS_THRESHOLD:
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

    def __del__(self):
        if self.pa is not None:
            self.pa.terminate()
