import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Porcupine Access Key for wake word detection
PORCUPINE_ACCESS_KEY = os.getenv("PORCUPINE_ACCESS_KEY")
