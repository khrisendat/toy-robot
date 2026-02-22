import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Google Cloud Service Account Key
# This is used for authenticating with Google Cloud services like Text-to-Speech and Speech-to-Text
SERVICE_ACCOUNT_KEY = "service-account-key.json"

# Audio Input Device Index
# Set AUDIO_INPUT_DEVICE_INDEX in your .env file
# Run 'arecord -l' on Raspberry Pi to find the correct device index
AUDIO_INPUT_DEVICE_INDEX = int(os.getenv("AUDIO_INPUT_DEVICE_INDEX", "0"))

# Child's name — used in speech and prompts
CHILD_NAME = os.getenv("CHILD_NAME", "Kabir")

