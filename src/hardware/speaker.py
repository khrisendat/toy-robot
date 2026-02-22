import subprocess
import os
from src import config

class Speaker:
    def __init__(self):
        # Path to Piper binary and model
        self.piper_binary = os.getenv("PIPER_BINARY", "/home/whoopsie/piper/piper")
        self.piper_model = os.getenv("PIPER_MODEL", "/home/whoopsie/piper/en_GB-alan-low.onnx")

        # Verify Piper is available
        if not os.path.exists(self.piper_binary):
            print(f"Warning: Piper binary not found at {self.piper_binary}")
        if not os.path.exists(self.piper_model):
            print(f"Warning: Piper model not found at {self.piper_model}")

        # Enable the Robot HAT speaker amplifier (GPIO pin 20)
        subprocess.run(["pinctrl", "set", "20", "op", "dh"],
                       capture_output=True)

    def say(self, text):
        """Synthesize and play text using Piper TTS."""
        try:
            print(f"Speaking: {text}", flush=True)

            # Clean text to remove problematic characters
            clean_text = text.replace('"', '').replace("'", "").replace("\n", " ")

            cmd = (
                f'echo "{clean_text}"'
                f' | {self.piper_binary} --model {self.piper_model} --output_raw'
                f' | sox -t raw -r 22050 -e signed -b 16 -c 1 - -t raw - norm'
                f' | aplay -D default -r 22050 -f S16_LE -t raw'
            )

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"Error during Piper TTS: {result.stderr}", flush=True)
        except Exception as e:
            print(f"Error during text-to-speech: {e}", flush=True)
