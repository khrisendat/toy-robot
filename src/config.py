import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Google Cloud Service Account Key
# This is used for authenticating with Google Cloud services like Text-to-Speech and Speech-to-Text
SERVICE_ACCOUNT_KEY = "service-account-key.json"

