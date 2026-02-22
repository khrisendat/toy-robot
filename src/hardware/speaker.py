import logging
import subprocess
import os

logger = logging.getLogger(__name__)

class Speaker:
    def __init__(self):
        self.piper_binary = os.getenv("PIPER_BINARY", "/home/whoopsie/piper/piper")
        self.piper_model = os.getenv("PIPER_MODEL", "/home/whoopsie/piper/en_GB-alan-low.onnx")

        if not os.path.exists(self.piper_binary):
            logger.warning(f"Piper binary not found at {self.piper_binary}")
        if not os.path.exists(self.piper_model):
            logger.warning(f"Piper model not found at {self.piper_model}")

        # Enable the Robot HAT speaker amplifier (GPIO pin 20)
        subprocess.run(["pinctrl", "set", "20", "op", "dh"], capture_output=True)

    def say(self, text):
        """Synthesize and play text using Piper TTS."""
        logger.info(f"Speaking: {text}")
        clean_text = text.replace('"', '').replace("'", "").replace("\n", " ")
        cmd = (
            f'echo "{clean_text}"'
            f' | {self.piper_binary} --model {self.piper_model} --output_raw'
            f' | sox -t raw -r 22050 -e signed -b 16 -c 1 - -t raw - norm'
            f' | aplay -D default -r 22050 -f S16_LE -t raw'
        )
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Piper TTS error: {result.stderr}")
        except Exception as e:
            logger.error(f"Text-to-speech error: {e}")
