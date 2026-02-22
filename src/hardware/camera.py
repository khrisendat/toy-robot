import io
import logging
import time
from picamera2 import Picamera2

logger = logging.getLogger(__name__)

class Camera:
    def __init__(self):
        self.cam = Picamera2()
        self.cam.configure(self.cam.create_still_configuration())
        self.cam.start()
        time.sleep(1)  # allow sensor to warm up
        logger.info("Camera ready.")

    def capture_jpeg(self):
        """Capture a single frame and return it as JPEG bytes, or None on failure."""
        try:
            buf = io.BytesIO()
            self.cam.capture_file(buf, format="jpeg")
            logger.debug(f"Captured {buf.tell()} byte JPEG frame.")
            return buf.getvalue()
        except Exception as e:
            logger.error(f"Failed to capture frame: {e}")
            return None

    def __del__(self):
        if hasattr(self, "cam"):
            try:
                self.cam.stop()
                self.cam.close()
            except Exception:
                pass
