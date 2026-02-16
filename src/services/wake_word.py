from vosk import Model, KaldiRecognizer
import pyaudio
import json
import os
import numpy as np
from src import config

class WakeWordDetector:
    def __init__(self):
        # Construct an absolute path to the model directory
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'models', 'vosk')
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"The Vosk model directory was not found at {model_path}. Please run the download script: ./scripts/download_model.sh")
        
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)
        
        self.pa = pyaudio.PyAudio()
        self.audio_stream = self.pa.open(
            rate=16000,
            channels=2,  # USB devices often require stereo (2 channels)
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=1024,
            input_device_index=config.AUDIO_INPUT_DEVICE_INDEX
        )
        self.wake_word = "hey robot"

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

    def wait_for_wake_word(self):
        print(f"Listening for '{self.wake_word}'...")
        while True:
            data = self.audio_stream.read(4096)
            # Convert stereo to mono for Vosk
            mono_data = self._stereo_to_mono(data)
            if self.recognizer.AcceptWaveform(mono_data):
                result = json.loads(self.recognizer.Result())
                if self.wake_word in result.get("text", ""):
                    print("Wake word detected!")
                    return

    def __del__(self):
        if hasattr(self, 'audio_stream') and self.audio_stream is not None:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        if hasattr(self, 'pa') and self.pa is not None:
            self.pa.terminate()
