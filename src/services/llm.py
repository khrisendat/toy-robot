import google.generativeai as genai
from .. import config

class LLMClient:
    def __init__(self):
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-flash')

    def generate_response(self, prompt):
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"An error occurred: {e}")
            return "I'm sorry, I'm having a little trouble thinking right now."
