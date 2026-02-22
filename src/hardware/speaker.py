import json
import logging
import os
import subprocess
import tempfile
import threading

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

        self._synthesis_done = threading.Event()
        self._start_piper()

    def _start_piper(self):
        logger.info(f"Starting persistent Piper TTS process (model: {self.piper_model})...")
        self._piper = subprocess.Popen(
            [self.piper_binary, "--model", self.piper_model,
             "--json-input", "--length_scale", "1.0",
             "--noise_scale", "1.0"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        threading.Thread(target=self._watch_stderr, daemon=True).start()
        logger.info("Piper TTS process ready.")

    def _watch_stderr(self):
        """Read Piper's stderr and signal when each utterance is synthesised."""
        for raw_line in self._piper.stderr:
            line = raw_line.decode().strip()
            logger.debug(f"Piper: {line}")
            if "Real-time factor" in line:
                self._synthesis_done.set()

    def say(self, text):
        logger.info(f"Speaking: {text}")
        clean_text = text.replace('"', '').replace("'", "").replace("\n", " ")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name

        try:
            self._synthesis_done.clear()
            payload = json.dumps({"text": clean_text, "output_file": tmp_path}) + "\n"
            self._piper.stdin.write(payload.encode())
            self._piper.stdin.flush()

            if not self._synthesis_done.wait(timeout=15):
                logger.error("Piper synthesis timed out.")
                return

            cmd = (
                f"sox {tmp_path} -t raw -r 22050 -e signed -b 16 -c 1 - norm pitch 450"
                f" | aplay -D default -r 22050 -f S16_LE -t raw"
            )
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Audio playback error: {result.stderr}")
        except Exception as e:
            logger.error(f"Text-to-speech error: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def __del__(self):
        if hasattr(self, "_piper") and self._piper.poll() is None:
            self._piper.terminate()
