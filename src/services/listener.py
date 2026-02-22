import logging
import time
import pyaudio
import numpy as np
from google.cloud import speech
from google.oauth2 import service_account
from src import config

logger = logging.getLogger(__name__)

class Listener:
    def __init__(self):
        credentials = service_account.Credentials.from_service_account_file(config.SERVICE_ACCOUNT_KEY)
        self.client = speech.SpeechClient(credentials=credentials)
        self.audio_config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
        )
        self.pa = pyaudio.PyAudio()

    def _stereo_to_mono(self, stereo_data):
        """Convert stereo audio data to mono by averaging channels."""
        audio = np.frombuffer(stereo_data, dtype=np.int16)
        audio = audio.reshape(-1, 2)
        mono = np.mean(audio, axis=1).astype(np.int16)
        return mono.tobytes()

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
        chunks_per_second = int(16000 / 1024)
        for i in range(total_chunks):
            data = stream.read(1024)
            mono_data = self._stereo_to_mono(data)
            frames.append(mono_data)
            if i % chunks_per_second == 0:
                seconds_left = duration - (i // chunks_per_second)
                logger.debug(f"Recording... {seconds_left}s left")

        stream.stop_stream()
        stream.close()

        logger.info("Finished recording. Sending to speech recognition...")
        start = time.time()

        audio_data = b"".join(frames)
        audio = speech.RecognitionAudio(content=audio_data)

        try:
            response = self.client.recognize(config=self.audio_config, audio=audio)
            if response.results:
                transcript = response.results[0].alternatives[0].transcript
                logger.info(f"Transcript ({time.time() - start:.2f}s): {transcript}")
                return transcript
            else:
                logger.info(f"No speech detected ({time.time() - start:.2f}s)")
                return ""
        except Exception as e:
            logger.error(f"Speech recognition error: {e}")
            return ""

    def __del__(self):
        if self.pa is not None:
            self.pa.terminate()
