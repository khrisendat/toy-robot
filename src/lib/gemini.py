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


class GeminiClient:
    def __init__(self, model: str = "gemini-2.5-flash-lite", timeout: int = 30):
        self.model = model
        self.timeout = timeout
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def generate(self, contents: list, system_prompt: str) -> str:
        """
        Send a generateContent request and return the response text.

        contents: list of {"role": ..., "parts": [...]} dicts
        Raises requests.Timeout or requests.HTTPError on failure.
        """
        response = requests.post(
            self.url,
            headers={"x-goog-api-key": config.GEMINI_API_KEY},
            json={
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": contents,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]

    @staticmethod
    def encode_audio(audio_bytes: bytes) -> dict:
        """Return an inlineData part for WAV audio."""
        return {
            "inlineData": {
                "mimeType": "audio/wav",
                "data": base64.b64encode(audio_bytes).decode(),
            }
        }

    @staticmethod
    def encode_image(image_bytes: bytes) -> dict:
        """Return an inlineData part for a JPEG image."""
        return {
            "inlineData": {
                "mimeType": "image/jpeg",
                "data": base64.b64encode(image_bytes).decode(),
            }
        }
