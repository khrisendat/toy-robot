import logging
import time
import requests
from .. import config

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.model = "gemini-3-flash-preview"
        self.timeout = 30  # seconds
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    def generate_response(self, prompt):
        logger.info(f"Sending to LLM ({self.model})...")
        logger.debug(f"Prompt: {prompt}")
        start = time.time()
        try:
            response = requests.post(
                self.url,
                params={"key": config.GEMINI_API_KEY},
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
