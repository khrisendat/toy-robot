import openwakeword
import pyaudio
import numpy as np

class WakeWordDetector:
    def __init__(self):
        # Initialize openwakeword
        self.oww = openwakeword.Model()
        
        # Initialize PyAudio
        self.pa = pyaudio.PyAudio()
        self.audio_stream = self.pa.open(
            rate=16000,  # openwakeword expects 16kHz sample rate
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=1280  # 80ms chunks
        )

    def wait_for_wake_word(self):
        print("Listening for wake word...")
        while True:
            # Read audio chunk
            audio_chunk = self.audio_stream.read(1280)
            
            # Convert to numpy array
            audio_np = np.frombuffer(audio_chunk, dtype=np.int16)
            
            # Process with openwakeword
            prediction = self.oww.predict(audio_np)
            
            # Check for wake word activation (any score > 0.5)
            if any(score > 0.5 for score in prediction.values()):
                print("Wake word detected!")
                # We can also see which one it was:
                # activated_models = [model for model, score in prediction.items() if score > 0.5]
                # print(f"Models activated: {activated_models}")
                return

    def __del__(self):
        if self.audio_stream is not None:
            self.audio_stream.close()
        if self.pa is not None:
            self.pa.terminate()
