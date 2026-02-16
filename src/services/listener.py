import pyaudio
import numpy as np
from google.cloud import speech
from google.oauth2 import service_account
from src import config

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
        # Convert bytes to numpy array of 16-bit integers
        audio = np.frombuffer(stereo_data, dtype=np.int16)
        # Reshape to (num_samples, 2) for stereo
        audio = audio.reshape(-1, 2)
        # Average the two channels to create mono
        mono = np.mean(audio, axis=1).astype(np.int16)
        # Convert back to bytes
        return mono.tobytes()

    def listen(self, duration=5):
        print("Listening for command...")
        
        stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=2,  # USB devices often require stereo (2 channels)
            rate=16000,
            input=True,
            frames_per_buffer=1024,
            input_device_index=config.AUDIO_INPUT_DEVICE_INDEX
        )

        frames = []
        for _ in range(0, int(16000 / 1024 * duration)):
            data = stream.read(1024)
            # Convert stereo to mono
            mono_data = self._stereo_to_mono(data)
            frames.append(mono_data)

        stream.stop_stream()
        stream.close()
        
        print("Finished listening.")

        audio_data = b"".join(frames)
        audio = speech.RecognitionAudio(content=audio_data)

        try:
            response = self.client.recognize(config=self.audio_config, audio=audio)
            if response.results:
                transcript = response.results[0].alternatives[0].transcript
                print(f"Transcript: {transcript}")
                return transcript
            else:
                print("No speech detected.")
                return ""
        except Exception as e:
            print(f"Error during speech recognition: {e}")
            return ""

    def __del__(self):
        if self.pa is not None:
            self.pa.terminate()
