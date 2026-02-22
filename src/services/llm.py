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

SYSTEM_PROMPT = (
    "You are a friendly robot assistant for a four-year-old named Kabir. "
    "Be kind, simple, and creative. Your response should be brief. "
    "Do not use emojis, asterisks, bullet points, or any special characters — only plain spoken words."
)

class LLMClient:
    def __init__(self):
        self.model = "gemini-2.5-flash-lite"
        self.timeout = 30  # seconds
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        self.history = []  # list of {"role": ..., "parts": [...]} dicts

    def generate_response(self, user_text):
        logger.info(f"Sending to LLM ({self.model})...")
        logger.debug(f"User: {user_text}")
        self.history.append({"role": "user", "parts": [{"text": user_text}]})
        start = time.time()
        try:
            response = requests.post(
                self.url,
                headers={"x-goog-api-key": config.GEMINI_API_KEY},
                json={
                    "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                    "contents": self.history,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            self.history.append({"role": "model", "parts": [{"text": text}]})
            logger.info(f"LLM response ({time.time() - start:.2f}s): {text}")
            return text
        except requests.Timeout:
            self.history.pop()  # remove the user message we just added
            logger.warning(f"LLM timed out after {time.time() - start:.2f}s")
            return "I'm sorry, I'm taking too long to think. Can you try again?"
        except Exception as e:
            self.history.pop()  # remove the user message we just added
            logger.error(f"LLM error after {time.time() - start:.2f}s: {e}")
            return "I'm sorry, I'm having a little trouble thinking right now."
