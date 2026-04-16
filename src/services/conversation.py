import logging
import time
from .. import config
from ..lib.gemini import GeminiClient

logger = logging.getLogger(__name__)

VISION_SIGNAL = "NEED_CAMERA"

BASE_SYSTEM_PROMPT = (
    f"You are a friendly robot assistant for a four-year-old named {config.CHILD_NAME}. "
    "Be kind, simple, and creative. Your response should be brief — just one or two sentences. "
    "Do not use emojis, asterisks, bullet points, or any special characters — only plain spoken words. "
    "Vary your tone and energy to keep things fun and surprising. "
    "About half the time, end your response with a simple, playful follow-up question to keep the conversation going. "
    f"If the child asks you to look at something or describe what you see, respond with exactly '{VISION_SIGNAL}' and nothing else."
)


class ConversationManager:
    def __init__(self, memory=None):
        self._client = GeminiClient()
        self._history = []  # list of {"role": ..., "parts": [...]} dicts (text only)
        self.memory = memory

    def generate_response(self, audio_data, get_image=None, store_memory=None):
        """
        Generate a response for the given input.

        audio_data: bytes (WAV) for real mic input, or str for mock/text input
        get_image:  optional callable() → bytes — invoked when the model requests vision
        store_memory: optional callable(user_text, robot_text) — called after a
                      successful response to persist the turn. Intended to be
                      wrapped in asyncio.create_task() by the caller so it does
                      not block the conversation loop.
        """
        logger.info(f"Sending to LLM ({self._client.model})...")

        if isinstance(audio_data, bytes):
            user_parts = [
                self._client.encode_audio(audio_data),
                {"text": "Respond to what the child said."},
            ]
            history_text = "[voice input]"
        else:
            user_parts = [{"text": audio_data}]
            history_text = audio_data

        system_prompt = self._build_system_prompt(history_text)
        start = time.time()

        try:
            text = self._call(user_parts, system_prompt)

            # If the model signals it needs the camera, capture and call again
            if text.strip() == VISION_SIGNAL and get_image is not None:
                logger.info("Vision requested — capturing image.")
                image_data = get_image()
                if image_data:
                    vision_parts = [
                        self._client.encode_image(image_data),
                        {"text": "Describe what you see in this image to the child in one or two fun sentences."},
                    ]
                    text = self._call(vision_parts, system_prompt)
                    history_text = "[asked to look]"
                else:
                    text = "I tried to look but my camera isn't working right now!"
                    history_text = "[camera failed]"

            # Safety net — never let the internal signal reach speech
            if text.strip() == VISION_SIGNAL:
                text = "I tried to look but I couldn't quite see. Can you describe it to me?"

            self._history.append({"role": "user", "parts": [{"text": history_text}]})
            self._history.append({"role": "model", "parts": [{"text": text}]})
            logger.info(f"LLM response ({time.time() - start:.2f}s): {text}")

            if store_memory is not None:
                store_memory(history_text, text)

            return text

        except Exception as e:
            elapsed = time.time() - start
            import requests as req
            if isinstance(e, req.Timeout):
                logger.warning(f"LLM timed out after {elapsed:.2f}s")
                return "I'm sorry, I'm taking too long to think. Can you try again?"
            logger.error(f"LLM error after {elapsed:.2f}s: {e}")
            return "I'm sorry, I'm having a little trouble thinking right now."

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _call(self, user_parts: list, system_prompt: str) -> str:
        contents = self._history + [{"role": "user", "parts": user_parts}]
        return self._client.generate(contents, system_prompt)

    def _build_system_prompt(self, query: str) -> str:
        if self.memory is None:
            return BASE_SYSTEM_PROMPT
        memories = self.memory.search(query, top_k=3)
        if not memories:
            return BASE_SYSTEM_PROMPT
        memory_block = "\n".join(f"- {m}" for m in memories)
        logger.debug(f"[Memory] Injecting {len(memories)} memories into prompt")
        return (
            BASE_SYSTEM_PROMPT
            + "\n\nRelevant memories from past conversations:\n"
            + memory_block
        )
