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

SYSTEM_PROMPT = (
    "You are a friendly robot assistant for a four-year-old named Kabir. "
    "Be kind, simple, and creative. Your response should be brief — just one or two sentences. "
    "Do not use emojis, asterisks, bullet points, or any special characters — only plain spoken words. "
    "Vary your tone and energy to keep things fun and surprising. "
    "About half the time, end your response with a simple, playful follow-up question to keep the conversation going."
)

class LLMClient:
    def __init__(self):
        self.model = "gemini-2.5-flash-lite"
        self.timeout = 30  # seconds
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        self.history = []  # list of {"role": ..., "parts": [...]} dicts (text only)

    def generate_response(self, audio_data):
        logger.info(f"Sending to LLM ({self.model})...")

        # Build the current user turn — audio for real mic, text for mock
        if isinstance(audio_data, bytes):
            encoded = base64.b64encode(audio_data).decode()
            current_user_parts = [
                {"inlineData": {"mimeType": "audio/wav", "data": encoded}},
                {"text": "Respond to what the child said."},
            ]
            history_user_text = "[voice input]"
        else:
            current_user_parts = [{"text": audio_data}]
            history_user_text = audio_data

        # Send full text history + current audio turn
        contents = self.history + [{"role": "user", "parts": current_user_parts}]

        start = time.time()
        try:
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
            text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            # Store text-only versions in history to keep payload small
            self.history.append({"role": "user", "parts": [{"text": history_user_text}]})
            self.history.append({"role": "model", "parts": [{"text": text}]})
            logger.info(f"LLM response ({time.time() - start:.2f}s): {text}")
            return text
        except requests.Timeout:
            logger.warning(f"LLM timed out after {time.time() - start:.2f}s")
            return "I'm sorry, I'm taking too long to think. Can you try again?"
        except Exception as e:
            logger.error(f"LLM error after {time.time() - start:.2f}s: {e}")
            return "I'm sorry, I'm having a little trouble thinking right now."
