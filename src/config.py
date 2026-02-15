import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

