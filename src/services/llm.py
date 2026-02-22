import requests
from .. import config

class LLMClient:
    def __init__(self):
        self.model = "gemini-3-flash-preview"
        self.timeout = 15  # seconds
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    def generate_response(self, prompt):
        print(f"Sending to LLM: {prompt}", flush=True)
        try:
            response = requests.post(
                self.url,
                params={"key": config.GEMINI_API_KEY},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=self.timeout,
            )
            response.raise_for_status()
            text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            print(f"LLM response: {text}", flush=True)
            return text
        except requests.Timeout:
            print(f"LLM request timed out after {self.timeout}s.", flush=True)
            return "I'm sorry, I'm taking too long to think. Can you try again?"
        except Exception as e:
            print(f"An error occurred: {e}", flush=True)
            return "I'm sorry, I'm having a little trouble thinking right now."
