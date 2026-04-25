import base64
import json
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
    def __init__(self, model: str = "gemini-2.5-flash", timeout: int = 30):
        self.model = model
        self.timeout = timeout
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def generate_stream(self, contents: list, system_prompt: str, tool_declarations=None, tool_config=None, thinking_budget: int = -1):
        """Yield text chunks (str) or a function call dict from the streaming endpoint.

        When tool_declarations are provided, yields either:
          str  — a text chunk to speak
          dict — {"function_call": {"name": ..., "args": {...}, "id": ...}}
        """
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models"
            f"/{self.model}:streamGenerateContent?alt=sse"
        )
        body = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": contents,
            "generationConfig": {"thinkingConfig": {"thinkingBudget": thinking_budget}},
        }
        if tool_declarations:
            body["tools"] = [{"function_declarations": tool_declarations}]
        if tool_config:
            body["toolConfig"] = tool_config
        response = requests.post(
            url,
            headers={"x-goog-api-key": config.GEMINI_API_KEY},
            json=body,
            stream=True,
            timeout=self.timeout,
        )
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode("utf-8")
            if not line.startswith("data: "):
                continue
            try:
                data = json.loads(line[6:])
                parts = data["candidates"][0]["content"]["parts"]
                for part in parts:
                    if part.get("thought"):
                        continue  # skip internal reasoning from gemini-2.5 thinking models
                    if "functionCall" in part:
                        fc = part["functionCall"]
                        yield {"function_call": {"name": fc["name"], "args": fc.get("args", {}), "id": fc.get("id")}}
                    elif "text" in part and part["text"]:
                        yield part["text"]
            except (json.JSONDecodeError, KeyError, IndexError):
                continue

    def generate_turn(self, contents: list, system_prompt: str, tool_declarations=None, tool_config=None, thinking_budget: int = -1) -> dict:
        """
        Send a generateContent request and return a dict with either:
          {"text": "..."}  — normal text response
          {"function_call": {"name": ..., "args": {...}, "id": ...}}  — tool invocation
        """
        body = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": contents,
            "generationConfig": {"thinkingConfig": {"thinkingBudget": thinking_budget}},
        }
        if tool_declarations:
            body["tools"] = [{"function_declarations": tool_declarations}]
        if tool_config:
            body["toolConfig"] = tool_config

        response = requests.post(
            self.url,
            headers={"x-goog-api-key": config.GEMINI_API_KEY},
            json=body,
            timeout=self.timeout,
        )
        response.raise_for_status()
        parts = response.json()["candidates"][0]["content"]["parts"]
        for part in parts:
            if part.get("thought"):
                continue  # skip internal reasoning from gemini-2.5 thinking models
            if "functionCall" in part:
                fc = part["functionCall"]
                return {"function_call": {"name": fc["name"], "args": fc.get("args", {}), "id": fc.get("id")}}
            if "text" in part:
                return {"text": part["text"]}
        return {"text": ""}

    def generate(self, contents: list, system_prompt: str) -> str:
        """Send a generateContent request and return the response text."""
        return self.generate_turn(contents, system_prompt).get("text", "")

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
