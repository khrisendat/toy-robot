#!/bin/bash
# Complete setup script for Kabir's Robot on Raspberry Pi
# This script handles all system dependencies and downloads

set -e  # Exit on any error

echo "======================================"
echo "Kabir's Robot - Raspberry Pi Setup"
echo "======================================"
echo ""

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "Warning: This script is designed for Raspberry Pi."
    echo "Some dependencies may not be available on other platforms."
    echo ""
fi

# System dependencies
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    libportaudio-dev \
    alsa-utils \
    curl \
    wget

echo "✓ System dependencies installed"
echo ""

# Python dependencies
echo "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo "Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✓ Python environment ready"
echo ""

# Vosk model
echo "Setting up Vosk wake word model..."
./scripts/download_model.sh
echo "✓ Vosk model ready"
echo ""

# Piper TTS
echo "Setting up Piper text-to-speech..."
./scripts/setup_piper.sh
echo "✓ Piper TTS ready"
echo ""

# Environment setup
echo "Setting up environment file..."
if [ ! -f ".env" ]; then
    cat > .env << EOF
# Gemini API Key for LLM responses
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE

# Audio input device index (run 'arecord -l' to find your microphone)
AUDIO_INPUT_DEVICE_INDEX=3

# Piper TTS configuration (optional, defaults shown below)
PIPER_BINARY=/home/whoopsie/piper/piper
PIPER_MODEL=/home/whoopsie/piper/en_GB-alan-low.onnx
EOF
    echo "Created .env file - please update GEMINI_API_KEY"
else
    echo ".env file already exists"
fi
echo ""

# Google Cloud setup instructions
echo "Google Cloud Setup Instructions:"
echo "=================================="
echo "1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts"
echo "2. Create a new service account"
echo "3. Grant it the 'Editor' role"
echo "4. Create and download a JSON key"
echo "5. Save it as 'service-account-key.json' in this directory"
echo ""

echo "======================================"
echo "✓ Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Update GEMINI_API_KEY in .env"
echo "2. Find your microphone: arecord -l"
echo "3. Update AUDIO_INPUT_DEVICE_INDEX in .env if needed"
echo "4. Add service-account-key.json for Google Cloud Speech-to-Text"
echo ""
echo "Then run: python3 main.py"
echo ""
