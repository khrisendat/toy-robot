import pvporcupine
import pyaudio
import struct
from .. import config

class WakeWordDetector:
    def __init__(self):
        self.porcupine = pvporcupine.create(
            access_key=config.PORCUPINE_ACCESS_KEY,
            keyword_paths=[pvporcupine.KEYWORD_PATHS["porcupine"]]
        )
        self.pa = pyaudio.PyAudio()
        self.audio_stream = self.pa.open(
            rate=self.porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.porcupine.frame_length
        )

    def wait_for_wake_word(self):
        print("Listening for wake word...")
        while True:
            pcm = self.audio_stream.read(self.porcupine.frame_length)
            pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)

            keyword_index = self.porcupine.process(pcm)

            if keyword_index >= 0:
                print("Wake word detected!")
                return

    def __del__(self):
        if self.porcupine is not None:
            self.porcupine.delete()

        if self.audio_stream is not None:
            self.audio_stream.close()

        if self.pa is not None:
            self.pa.terminate()
