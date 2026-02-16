from vosk import Model, KaldiRecognizer
import pyaudio
import json
import os

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
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=1024,
            input_device_index=3 # Specify the correct input device index
        )
        self.wake_word = "hey robot"

    def wait_for_wake_word(self):
        print(f"Listening for '{self.wake_word}'...")
        while True:
            data = self.audio_stream.read(4096)
            if self.recognizer.AcceptWaveform(data):
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
