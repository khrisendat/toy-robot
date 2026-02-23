import logging
import random
import threading
import time

logger = logging.getLogger(__name__)

STEER_MIN, STEER_MAX = -30, 30


class Wheels:
    def __init__(self):
        try:
            from picarx import Picarx
            self._car = Picarx()
            self._available = True
            logger.info("Wheels initialised.")
        except Exception as e:
            logger.warning(f"Wheels unavailable: {e}")
            self._available = False

        self._running = False
        self._thread = None
        self.stop()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def idle(self):
        """Small random wiggles — used while waiting for the wake word."""
        logger.debug("Wheels entering idle animation.")
        self._start_animation(self._idle_loop)

    def stop(self):
        """Stop all movement and straighten steering."""
        self._stop_animation()
        if self._available:
            try:
                self._car.set_dir_servo_angle(0)
                self._car.stop()
            except Exception as e:
                logger.debug(f"Wheels stop error: {e}")
        logger.debug("Wheels stopped.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _start_animation(self, loop_fn):
        self._stop_animation()
        self._running = True
        self._thread = threading.Thread(target=loop_fn, daemon=True)
        self._thread.start()

    def _stop_animation(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self._thread = None

    def _idle_loop(self):
        """Pause, nudge in a random direction, pause again — repeat."""
        while self._running:
            # Rest between moves
            rest = random.uniform(3.0, 6.0)
            deadline = time.time() + rest
            while self._running and time.time() < deadline:
                time.sleep(0.1)

            if not self._running:
                return

            # Pick a random steering angle and direction
            angle = random.choice([-20, -15, 15, 20])
            go = random.choice([True, False])  # forward or backward
            speed = random.randint(10, 20)
            move_time = random.uniform(0.3, 0.7)

            if self._available:
                try:
                    self._car.set_dir_servo_angle(angle)
                    if go:
                        self._car.forward(speed)
                    else:
                        self._car.backward(speed)
                except Exception as e:
                    logger.debug(f"Wheels move error: {e}")

            deadline = time.time() + move_time
            while self._running and time.time() < deadline:
                time.sleep(0.05)

            if self._available:
                try:
                    self._car.stop()
                    self._car.set_dir_servo_angle(0)
                except Exception as e:
                    logger.debug(f"Wheels stop error: {e}")

    def __del__(self):
        self._stop_animation()
        if self._available:
            try:
                self._car.stop()
            except Exception:
                pass
