import asyncio
import logging
import re

from src import config
from src.hardware.speaker import Speaker
from src.hardware.head import Head
from src.hardware.camera import Camera
from src.hardware.grayscale import GrayscaleSensor
from src.hardware.wheels import Wheels
from src.services.api import WakeWordDetector, Listener
from src.services.llm import LLMClient

_log_format = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
_log_datefmt = "%H:%M:%S"

logging.basicConfig(level=logging.DEBUG, format=_log_format, datefmt=_log_datefmt)
_file_handler = logging.FileHandler("robot.log")
_file_handler.setFormatter(logging.Formatter(_log_format, datefmt=_log_datefmt))
logging.getLogger().addHandler(_file_handler)
logger = logging.getLogger(__name__)

# Safety thresholds
BATTERY_LOW_THRESHOLD = 7.0       # volts — log only
BATTERY_CRITICAL_THRESHOLD = 6.0  # volts — speak warning
BATTERY_WARN_COOLDOWN = 30.0      # seconds between repeated critical battery warnings
CLIFF_WARN_COOLDOWN = 10.0        # seconds between repeated cliff warnings
SAFETY_INTERVAL = 1.0             # seconds between safety checks


def sanitize_for_speech(text):
    """Remove characters that TTS cannot speak meaningfully."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub("", text)
    text = re.sub(r"[*#_~`|<>^]", "", text)
    text = re.sub(r" +", " ", text)
    return text.strip()


async def run(func, *args):
    """Run a blocking function in the default thread pool executor."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, func, *args)


async def say(speaker, speech_lock, text):
    """Speak text, serialised through speech_lock to prevent overlap."""
    async with speech_lock:
        await run(speaker.say, text)


async def conversation_loop(speaker, head, wheels, camera, speech_lock):
    wake_word = WakeWordDetector()
    listener = Listener()
    llm = LLMClient()

    while True:
        # Wait for wake word
        head.idle()
        wheels.idle()
        await run(wake_word.wait_for_wake_word)
        head.center()
        wheels.stop()

        # Listen for command — up to 3 attempts
        head.listening()
        audio = None
        for attempt in range(3):
            if attempt > 0:
                logger.info(f"Didn't catch that. Listening again... (attempt {attempt + 1}/3)")
            audio = await run(listener.listen)
            if audio is not None:
                break

        if audio is None:
            logger.warning("No command heard after 3 attempts. Going back to wake word.")
            head.center()
            continue

        # Get LLM response
        response = await run(llm.generate_response, audio, camera.capture_jpeg)
        cleaned = sanitize_for_speech(response)

        # Speak response
        head.speaking()
        await say(speaker, speech_lock, cleaned)
        head.center()


async def safety_monitor(speaker, grayscale, speech_lock):
    last_battery_warned = 0.0
    last_cliff_warned = 0.0

    while True:
        await asyncio.sleep(SAFETY_INTERVAL)
        loop = asyncio.get_running_loop()

        # Battery check
        try:
            from robot_hat import get_battery_voltage
            voltage = await run(get_battery_voltage)
            logger.debug(f"[Safety] Battery: {voltage:.2f}V")
            if voltage < BATTERY_CRITICAL_THRESHOLD:
                logger.error(f"[Safety] Battery critical: {voltage:.2f}V")
                if loop.time() - last_battery_warned >= BATTERY_WARN_COOLDOWN:
                    await say(speaker, speech_lock, "My battery is very low. Please plug me in!")
                    last_battery_warned = loop.time()
            elif voltage < BATTERY_LOW_THRESHOLD:
                logger.warning(f"[Safety] Battery low: {voltage:.2f}V")
        except Exception as e:
            logger.debug(f"[Safety] Battery read failed: {e}")

        # Cliff check
        values = await run(grayscale.read)
        if values is not None:
            logger.debug(f"[Safety] Grayscale: L={values[0]} M={values[1]} R={values[2]}")
            if grayscale.is_cliff(values=values):
                logger.warning(f"[Safety] Cliff detected! Readings: {values}")
                if loop.time() - last_cliff_warned >= CLIFF_WARN_COOLDOWN:
                    await say(speaker, speech_lock,
                              f"Whoa! I'm going to fall! {config.CHILD_NAME}, can you save me?")
                    last_cliff_warned = loop.time()


async def main():
    speaker = Speaker()
    head = Head()
    wheels = Wheels()
    camera = Camera()
    grayscale = GrayscaleSensor()
    speech_lock = asyncio.Lock()

    logger.info("Starting robot...")
    await say(speaker, speech_lock, f"Hey {config.CHILD_NAME}! I'm awake!")

    try:
        await asyncio.gather(
            conversation_loop(speaker, head, wheels, camera, speech_lock),
            safety_monitor(speaker, grayscale, speech_lock),
        )
    except asyncio.CancelledError:
        logger.info("Robot shutting down...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Robot shutting down...")
