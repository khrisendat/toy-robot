import logging
import os
import subprocess
import tempfile

logger = logging.getLogger(__name__)

DEFAULT_VOICE = "Daniel"


class MacOSSpeaker:
    def __init__(self, voice=DEFAULT_VOICE):
        self.voice = voice

    def say(self, text):
        logger.info(f"Speaking: {text}")
        try:
            subprocess.run(["say", "-v", self.voice, text], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Text-to-speech error: {e}")

    def synthesize(self, text: str) -> bytes:
        """Return WAV bytes for the given text using the macOS say command."""
        aiff_path = tempfile.mktemp(suffix=".aiff")
        wav_path = tempfile.mktemp(suffix=".wav")
        try:
            subprocess.run(["say", "-v", self.voice, "-o", aiff_path, text], check=True)
            subprocess.run(
                ["afconvert", "-f", "WAVE", "-d", "LEI16@22050", aiff_path, wav_path],
                check=True,
            )
            with open(wav_path, "rb") as f:
                return f.read()
        except subprocess.CalledProcessError as e:
            logger.error(f"TTS synthesis error: {e}")
            return b""
        finally:
            for path in (aiff_path, wav_path):
                if os.path.exists(path):
                    os.unlink(path)
