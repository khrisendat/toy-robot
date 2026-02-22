import logging
import json
import os
import numpy as np
import pyaudio
from vosk import Model, KaldiRecognizer
from src import config

logger = logging.getLogger(__name__)

class WakeWordDetector:
    def __init__(self):
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'models', 'vosk')
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"The Vosk model directory was not found at {model_path}. Please run the download script: ./scripts/download_model.sh")

        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000, '["hey robot", "[unk]"]')

        self.pa = pyaudio.PyAudio()
        self.channels = self._get_supported_channels(config.AUDIO_INPUT_DEVICE_INDEX)
        self.audio_stream = self._open_stream(config.AUDIO_INPUT_DEVICE_INDEX)
        self.wake_word = "hey robot"

    def _get_supported_channels(self, device_index):
        device_info = self.pa.get_device_info_by_index(device_index)
        max_channels = int(device_info.get("maxInputChannels", 1))
        return 2 if max_channels >= 2 else 1

    def _open_stream(self, device_index):
        """Open audio stream, falling back to mono if stereo fails."""
        for channels in ([self.channels] if self.channels == 1 else [self.channels, 1]):
            try:
                stream = self.pa.open(
                    rate=16000,
                    channels=channels,
                    format=pyaudio.paInt16,
                    input=True,
                    frames_per_buffer=1024,
                    input_device_index=device_index
                )
                self.channels = channels
                return stream
            except OSError:
                logger.warning(f"Failed to open stream with {channels} channel(s), trying fewer...")
        raise OSError("Could not open audio stream with any channel count.")

    def _to_mono(self, data):
        if self.channels == 1:
            return data
        audio = np.frombuffer(data, dtype=np.int16)
        audio = audio.reshape(-1, self.channels)
        mono = np.mean(audio, axis=1).astype(np.int16)
        return mono.tobytes()

    def wait_for_wake_word(self):
        logger.info(f"Listening for '{self.wake_word}'...")
        while True:
            data = self.audio_stream.read(4096)
            mono_data = self._to_mono(data)
            if self.recognizer.AcceptWaveform(mono_data):
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "")
                if text:
                    logger.debug(f"Heard: '{text}'")
                if self.wake_word in text:
                    logger.info("Wake word detected!")
                    return
            else:
                partial = json.loads(self.recognizer.PartialResult()).get("partial", "")
                if partial:
                    logger.debug(f"Partial: '{partial}'")
                    if self.wake_word in partial:
                        logger.info("Wake word detected!")
                        return

    def __del__(self):
        if hasattr(self, 'audio_stream') and self.audio_stream is not None:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        if hasattr(self, 'pa') and self.pa is not None:
            self.pa.terminate()
