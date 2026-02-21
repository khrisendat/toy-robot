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
        self.channels = self._get_supported_channels(config.AUDIO_INPUT_DEVICE_INDEX)
        self.audio_stream = self.pa.open(
            rate=16000,
            channels=self.channels,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=1024,
            input_device_index=config.AUDIO_INPUT_DEVICE_INDEX
        )
        self.wake_word = "hey robot"

    def _get_supported_channels(self, device_index):
        """Detect the number of channels supported by the input device."""
        device_info = self.pa.get_device_info_by_index(device_index)
        max_channels = int(device_info.get("maxInputChannels", 1))
        if max_channels >= 2:
            return 2
        return 1

    def _to_mono(self, data):
        """Convert audio data to mono if it is stereo."""
        if self.channels == 1:
            return data
        # Convert bytes to numpy array of 16-bit integers
        audio = np.frombuffer(data, dtype=np.int16)
        # Reshape to (num_samples, channels) and average across channels
        audio = audio.reshape(-1, self.channels)
        mono = np.mean(audio, axis=1).astype(np.int16)
        return mono.tobytes()

    def wait_for_wake_word(self):
        print(f"Listening for '{self.wake_word}'...")
        while True:
            data = self.audio_stream.read(4096)
            mono_data = self._to_mono(data)
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
