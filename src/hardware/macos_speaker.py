import logging
import subprocess

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
