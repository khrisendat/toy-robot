import asyncio
import logging
import re

from src import config
from src.hardware.macos_speaker import MacOSSpeaker
from src.hardware.wake_word import WakeWordDetector
from src.hardware.macos_listener import MacOSListener
from src.services.conversation import ConversationManager
from src.lib.memory import MemoryStore

_log_format = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
_log_datefmt = "%H:%M:%S"

logging.basicConfig(level=logging.INFO, format=_log_format, datefmt=_log_datefmt)
_file_handler = logging.FileHandler("mac_conversation.log")
_file_handler.setFormatter(logging.Formatter(_log_format, datefmt=_log_datefmt))
logging.getLogger().addHandler(_file_handler)
logger = logging.getLogger(__name__)


def sanitize_for_speech(text):
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
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, func, *args)


async def say(speaker, speech_lock, text):
    async with speech_lock:
        await run(speaker.say, text)


async def conversation_loop(speaker, speech_lock, memory):
    wake_word = WakeWordDetector()
    listener = MacOSListener()
    llm = ConversationManager(memory=memory)

    while True:
        await run(wake_word.wait_for_wake_word)

        audio = None
        for attempt in range(3):
            if attempt > 0:
                logger.info(f"Didn't catch that. Listening again... (attempt {attempt + 1}/3)")
            audio = await run(listener.listen)
            if audio is not None:
                break

        if audio is None:
            logger.warning("No command heard after 3 attempts. Going back to wake word.")
            continue

        def store_turn(user_text, robot_text):
            memory.store(user_text, robot_text)

        loop = asyncio.get_running_loop()
        sentence_queue = asyncio.Queue()

        def stream_sentences():
            try:
                for sentence in llm.generate_response_stream(audio, None, store_turn):
                    loop.call_soon_threadsafe(sentence_queue.put_nowait, sentence)
            finally:
                loop.call_soon_threadsafe(sentence_queue.put_nowait, None)

        loop.run_in_executor(None, stream_sentences)

        while True:
            sentence = await sentence_queue.get()
            if sentence is None:
                break
            await say(speaker, speech_lock, sanitize_for_speech(sentence))


async def main():
    speaker = MacOSSpeaker()
    memory = MemoryStore()
    speech_lock = asyncio.Lock()

    logger.info("Starting macOS conversation...")
    await say(speaker, speech_lock, f"Hey {config.CHILD_NAME}! I'm awake!")

    try:
        await conversation_loop(speaker, speech_lock, memory)
    except asyncio.CancelledError:
        logger.info("Shutting down...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
