from google import genai
from .. import config

class LLMClient:
    def __init__(self):
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model = "gemini-2.5-flash"

    def generate_response(self, prompt):
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            return response.text
        except Exception as e:
            print(f"An error occurred: {e}")
            return "I'm sorry, I'm having a little trouble thinking right now."
