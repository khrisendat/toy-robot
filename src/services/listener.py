import pyaudio
from google.cloud import speech

class Listener:
    def __init__(self):
        self.client = speech.SpeechClient()
        self.audio_config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
        )
        self.pa = pyaudio.PyAudio()

    def listen(self, duration=5):
        print("Listening for command...")
        
        stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )

        frames = []
        for _ in range(0, int(16000 / 1024 * duration)):
            data = stream.read(1024)
            frames.append(data)

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
