import logging
import py_trees
from src import config

logger = logging.getLogger(__name__)

BATTERY_LOW_THRESHOLD = 7.0      # volts — warn but continue
BATTERY_CRITICAL_THRESHOLD = 6.4 # volts — block conversation

def _read_battery_voltage():
    """Read battery voltage from Robot HAT. Returns None if unavailable."""
    try:
        from robot_hat import get_battery_voltage
        return get_battery_voltage()
    except Exception as e:
        logger.debug(f"Battery read failed: {e}")
        return None


class CheckBattery(py_trees.behaviour.Behaviour):
    """
    Safety guard that runs on every tree tick.

    Returns FAILURE when battery is OK so the Selector moves on to the
    Conversation branch. Returns SUCCESS when battery is critical, which
    blocks the Selector from reaching Conversation.
    """

    def __init__(self, speaker, name="CheckBattery"):
        super().__init__(name)
        self.speaker = speaker
        self._low_warned = False  # only warn once per session

    def update(self):
        voltage = _read_battery_voltage()

        if voltage is None:
            logger.debug("Battery voltage unavailable, skipping check.")
            return py_trees.common.Status.FAILURE

        logger.debug(f"Battery voltage: {voltage:.2f}V")

        if voltage < BATTERY_CRITICAL_THRESHOLD:
            logger.error(f"Battery critical: {voltage:.2f}V (threshold: {BATTERY_CRITICAL_THRESHOLD}V)")
            self.speaker.say("My battery is very low. Please plug me in!")
            return py_trees.common.Status.SUCCESS  # blocks Conversation

        if voltage < BATTERY_LOW_THRESHOLD and not self._low_warned:
            logger.warning(f"Battery low: {voltage:.2f}V (threshold: {BATTERY_LOW_THRESHOLD}V)")
            self.speaker.say(f"Just so you know {config.CHILD_NAME}, my battery is getting low.")
            self._low_warned = True
            return py_trees.common.Status.FAILURE  # continue normally

        return py_trees.common.Status.FAILURE  # battery OK, continue normally
