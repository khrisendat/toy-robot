import base64
import logging
import socket
import time
import requests
from .. import config

# Force IPv4 — Pi's IPv6 stack causes ~120s delays before falling back
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(*args, **kwargs):
    return [r for r in _orig_getaddrinfo(*args, **kwargs) if r[0] == socket.AF_INET]
socket.getaddrinfo = _ipv4_getaddrinfo

logger = logging.getLogger(__name__)

VISION_SIGNAL = "NEED_CAMERA"

SYSTEM_PROMPT = (
    "You are a friendly robot assistant for a four-year-old named Kabir. "
    "Be kind, simple, and creative. Your response should be brief — just one or two sentences. "
    "Do not use emojis, asterisks, bullet points, or any special characters — only plain spoken words. "
    "Vary your tone and energy to keep things fun and surprising. "
    "About half the time, end your response with a simple, playful follow-up question to keep the conversation going. "
    f"If the child asks you to look at something or describe what you see, respond with exactly '{VISION_SIGNAL}' and nothing else."
)

class LLMClient:
    def __init__(self):
        self.model = "gemini-2.5-flash-lite"
        self.timeout = 30  # seconds
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        self.history = []  # list of {"role": ..., "parts": [...]} dicts (text only)

    def _call(self, user_parts):
        """Make a single API call with the given user parts and return the response text."""
        contents = self.history + [{"role": "user", "parts": user_parts}]
        response = requests.post(
            self.url,
            headers={"x-goog-api-key": config.GEMINI_API_KEY},
            json={
                "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": contents,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]

    def generate_response(self, audio_data, get_image=None):
        logger.info(f"Sending to LLM ({self.model})...")

        # Build user parts — audio for real mic, text for mock
        if isinstance(audio_data, bytes):
            encoded = base64.b64encode(audio_data).decode()
            user_parts = [
                {"inlineData": {"mimeType": "audio/wav", "data": encoded}},
                {"text": "Respond to what the child said."},
            ]
            history_text = "[voice input]"
        else:
            user_parts = [{"text": audio_data}]
            history_text = audio_data

        start = time.time()
        try:
            text = self._call(user_parts)

            # If Gemini signals it needs the camera, capture and call again
            if text.strip() == VISION_SIGNAL and get_image is not None:
                logger.info("Vision requested — capturing image.")
                image_data = get_image()
                if image_data:
                    encoded_image = base64.b64encode(image_data).decode()
                    vision_parts = user_parts + [
                        {"inlineData": {"mimeType": "image/jpeg", "data": encoded_image}}
                    ]
                    text = self._call(vision_parts)
                    history_text = "[asked to look]"

            self.history.append({"role": "user", "parts": [{"text": history_text}]})
            self.history.append({"role": "model", "parts": [{"text": text}]})
            logger.info(f"LLM response ({time.time() - start:.2f}s): {text}")
            return text

        except requests.Timeout:
            logger.warning(f"LLM timed out after {time.time() - start:.2f}s")
            return "I'm sorry, I'm taking too long to think. Can you try again?"
        except Exception as e:
            logger.error(f"LLM error after {time.time() - start:.2f}s: {e}")
            return "I'm sorry, I'm having a little trouble thinking right now."
