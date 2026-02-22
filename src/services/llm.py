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

class LLMClient:
    def __init__(self):
        self.model = "gemini-2.5-flash-lite"
        self.timeout = 30  # seconds
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    def generate_response(self, prompt):
        logger.info(f"Sending to LLM ({self.model})...")
        logger.debug(f"Prompt: {prompt}")
        start = time.time()
        try:
            response = requests.post(
                self.url,
                headers={"x-goog-api-key": config.GEMINI_API_KEY},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=self.timeout,
            )
            response.raise_for_status()
            text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            logger.info(f"LLM response ({time.time() - start:.2f}s): {text}")
            return text
        except requests.Timeout:
            logger.warning(f"LLM timed out after {time.time() - start:.2f}s")
            return "I'm sorry, I'm taking too long to think. Can you try again?"
        except Exception as e:
            logger.error(f"LLM error after {time.time() - start:.2f}s: {e}")
            return "I'm sorry, I'm having a little trouble thinking right now."
