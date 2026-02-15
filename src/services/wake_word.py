import openwakeword
import pyaudio
import numpy as np

class WakeWordDetector:
    def __init__(self):
        # Initialize openwakeword to only listen for "Hey Jarvis"
        self.oww = openwakeword.Model(wakeword_models=["hey_jarvis"])
        
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
        print("Listening for 'Hey Jarvis'...")
        while True:
            # Read audio chunk
            audio_chunk = self.audio_stream.read(1280)
            
            # Convert to numpy array
            audio_np = np.frombuffer(audio_chunk, dtype=np.int16)
            
            # Process with openwakeword
            prediction = self.oww.predict(audio_np)
            
            # Check for 'hey_jarvis' activation
            if prediction.get("hey_jarvis", 0) > 0.5:
                print("Wake word 'Hey Jarvis' detected!")
                return

    def __del__(self):
        if self.audio_stream is not None:
            self.audio_stream.close()
        if self.pa is not None:
            self.pa.terminate()
