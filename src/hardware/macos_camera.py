import logging
import time

import cv2

logger = logging.getLogger(__name__)

_WARMUP_FRAMES = 5
_CAPTURE_RETRIES = 5


def _find_builtin_camera():
    """Return the highest-index camera available — the built-in FaceTime camera is typically
    at a higher index than Continuity Camera (iPhone) when both are present."""
    best_idx = 0
    for i in range(6):
        cap = cv2.VideoCapture(i)
        opened = cap.isOpened()
        cap.release()
        if opened:
            best_idx = i
        elif best_idx > 0 or i > 0:
            break  # stop at first gap after finding something
    logger.info(f"Using camera index {best_idx}")
    return cv2.VideoCapture(best_idx)


class MacOSCamera:
    def __init__(self):
        self.cam = _find_builtin_camera()
        if not self.cam.isOpened():
            logger.error("Could not open webcam.")
            return
        # Discard initial frames — macOS needs a moment before returning real data
        for _ in range(_WARMUP_FRAMES):
            self.cam.read()
        logger.info("Camera ready.")

    def capture_jpeg(self):
        """Capture a single frame and return it as JPEG bytes, or None on failure."""
        for attempt in range(_CAPTURE_RETRIES):
            ret, frame = self.cam.read()
            if ret:
                break
            time.sleep(0.05)
        else:
            logger.error("Failed to capture frame after retries.")
            return None
        ret, buf = cv2.imencode(".jpg", frame)
        if not ret:
            logger.error("Failed to encode frame as JPEG.")
            return None
        logger.debug(f"Captured {len(buf)} byte JPEG frame.")
        return buf.tobytes()

    def __del__(self):
        if hasattr(self, "cam") and self.cam.isOpened():
            self.cam.release()
