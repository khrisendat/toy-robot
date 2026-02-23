import logging
import random
import threading
import time

logger = logging.getLogger(__name__)

PAN_MIN, PAN_MAX = -30, 30
TILT_MIN, TILT_MAX = -10, 20


class Head:
    def __init__(self):
        try:
            from robot_hat import Servo
            self._pan = Servo('P0')
            self._tilt = Servo('P1')
            self._available = True
            logger.info("Head servos initialised.")
        except Exception as e:
            logger.warning(f"Head servos unavailable: {e}")
            self._available = False

        self._pan_angle = 0
        self._tilt_angle = 0
        self._running = False
        self._thread = None
        self.center()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def center(self):
        """Return to neutral position and stop any animation."""
        self._stop_animation()
        self._move_pan(0)
        self._move_tilt(0)
        logger.debug("Head centred.")

    def idle(self):
        """Slowly look around — used while waiting for the wake word."""
        logger.debug("Head entering idle animation.")
        self._start_animation(self._idle_loop)

    def listening(self):
        """Tilt head curiously — used while recording a command."""
        self._stop_animation()
        self._move_pan(0)
        self._move_tilt(15)
        logger.debug("Head in listening pose.")

    def speaking(self):
        """Quick nod then hold — used while the robot speaks."""
        logger.debug("Head entering speaking animation.")
        self._start_animation(self._speaking_loop)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _move_pan(self, angle):
        angle = max(PAN_MIN, min(PAN_MAX, int(angle)))
        if self._available:
            self._pan.angle(angle)
        self._pan_angle = angle

    def _move_tilt(self, angle):
        angle = max(TILT_MIN, min(TILT_MAX, int(angle)))
        if self._available:
            self._tilt.angle(angle)
        self._tilt_angle = angle

    def _start_animation(self, loop_fn):
        self._stop_animation()
        self._running = True
        self._thread = threading.Thread(target=loop_fn, daemon=True)
        self._thread.start()

    def _stop_animation(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def _idle_loop(self):
        """Gradually move to random pan/tilt positions, pausing between each."""
        while self._running:
            target_pan = random.randint(-25, 25)
            target_tilt = random.randint(-5, 12)
            steps = 30
            start_pan = self._pan_angle
            start_tilt = self._tilt_angle
            for i in range(1, steps + 1):
                if not self._running:
                    return
                self._move_pan(start_pan + (target_pan - start_pan) * i / steps)
                self._move_tilt(start_tilt + (target_tilt - start_tilt) * i / steps)
                time.sleep(0.04)

            hold = random.uniform(1.5, 3.5)
            deadline = time.time() + hold
            while self._running and time.time() < deadline:
                time.sleep(0.1)

    def _speaking_loop(self):
        """Single nod then hold at a slight forward tilt."""
        self._move_tilt(-8)
        time.sleep(0.15)
        self._move_tilt(5)
        time.sleep(0.15)
        self._move_tilt(0)
        while self._running:
            time.sleep(0.1)

    def __del__(self):
        self._stop_animation()
        if self._available:
            try:
                self._move_pan(0)
                self._move_tilt(0)
            except Exception:
                pass
