import logging

logger = logging.getLogger(__name__)

CLIFF_THRESHOLD = 200  # ADC value (0-4095) below which a sensor sees no surface


class GrayscaleSensor:
    def __init__(self):
        try:
            from robot_hat import Grayscale_Module, ADC
            self._sensor = Grayscale_Module(ADC('A0'), ADC('A1'), ADC('A2'))
            self._available = True
            logger.info("Grayscale sensor initialised.")
        except Exception as e:
            logger.warning(f"Grayscale sensor unavailable: {e}")
            self._available = False

    def read(self):
        """Returns [left, middle, right] ADC values (0-4095), or None if unavailable."""
        if not self._available:
            return None
        try:
            return self._sensor.read()
        except Exception as e:
            logger.debug(f"Grayscale read failed: {e}")
            return None

    def is_cliff(self, values=None, threshold=CLIFF_THRESHOLD):
        """Returns True if any sensor detects no surface (possible cliff/edge).

        Pass pre-read values to avoid a second ADC read.
        """
        if values is None:
            values = self.read()
        if values is None:
            return False
        return any(v < threshold for v in values)
