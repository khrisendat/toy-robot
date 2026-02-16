#!/bin/bash
# Troubleshooting and diagnostics script for Kabir's Robot

echo "======================================"
echo "Kabir's Robot - Troubleshooting Guide"
echo "======================================"
echo ""

# Check Python
echo "1. Checking Python..."
python3 --version
if python3 -c "import venv" 2>/dev/null; then
    echo "   ✓ Python venv available"
else
    echo "   ✗ Python venv not available - install python3-venv"
fi
echo ""

# Check virtual environment
echo "2. Checking virtual environment..."
if [ -f "venv/bin/activate" ]; then
    echo "   ✓ Virtual environment exists at venv/"
    if [ -z "$VIRTUAL_ENV" ]; then
        echo "   Note: Virtual environment not activated. Run: source venv/bin/activate"
    else
        echo "   ✓ Virtual environment is activated"
    fi
else
    echo "   ✗ Virtual environment not found. Run: python3 -m venv venv"
fi
echo ""

# Check Python packages
echo "3. Checking Python packages..."
python3 -c "import py_trees" 2>/dev/null && echo "   ✓ py_trees" || echo "   ✗ py_trees (run: pip install py_trees)"
python3 -c "import vosk" 2>/dev/null && echo "   ✓ vosk" || echo "   ✗ vosk (run: pip install vosk)"
python3 -c "import pyaudio" 2>/dev/null && echo "   ✓ pyaudio" || echo "   ✗ pyaudio (run: pip install pyaudio)"
python3 -c "import numpy" 2>/dev/null && echo "   ✓ numpy" || echo "   ✗ numpy (run: pip install numpy)"
python3 -c "from google.cloud import speech" 2>/dev/null && echo "   ✓ google-cloud-speech" || echo "   ✗ google-cloud-speech (run: pip install google-cloud-speech)"
python3 -c "from google import genai" 2>/dev/null && echo "   ✓ google-genai" || echo "   ✗ google-genai (run: pip install google-genai)"
echo ""

# Check Vosk model
echo "4. Checking Vosk model..."
if [ -d "models/vosk" ]; then
    echo "   ✓ Vosk model directory exists"
    if [ -f "models/vosk/model.fst" ]; then
        echo "   ✓ Vosk model files found"
    else
        echo "   ✗ Vosk model files incomplete. Run: ./scripts/download_model.sh"
    fi
else
    echo "   ✗ Vosk model not found. Run: ./scripts/download_model.sh"
fi
echo ""

# Check Piper (Raspberry Pi only)
if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "5. Checking Piper TTS (Raspberry Pi)..."
    if [ -f "/home/whoopsie/piper/piper" ]; then
        echo "   ✓ Piper binary found"
    else
        echo "   ✗ Piper binary not found. Run: ./scripts/setup_piper.sh"
    fi
    
    if [ -f "/home/whoopsie/piper/en_GB-alan-low.onnx" ]; then
        echo "   ✓ Piper voice model found"
    else
        echo "   ✗ Piper voice model not found. Run: ./scripts/setup_piper.sh"
    fi
    echo ""
    
    # Check audio devices
    echo "6. Checking audio devices..."
    if command -v arecord &> /dev/null; then
        echo "   ✓ arecord found"
        echo ""
        echo "   Available audio devices:"
        arecord -l | grep "card"
    else
        echo "   ✗ arecord not found. Install with: sudo apt-get install alsa-utils"
    fi
    echo ""
fi

# Check environment file
echo "7. Checking .env file..."
if [ -f ".env" ]; then
    echo "   ✓ .env file exists"
    if grep -q "GEMINI_API_KEY" .env; then
        if grep -q "GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE" .env; then
            echo "   ⚠ GEMINI_API_KEY not set - update your .env file"
        else
            echo "   ✓ GEMINI_API_KEY is set"
        fi
    else
        echo "   ✗ GEMINI_API_KEY not in .env"
    fi
else
    echo "   ✗ .env file not found. Create one with your API keys."
fi
echo ""

# Check service account key
echo "8. Checking Google Cloud credentials..."
if [ -f "service-account-key.json" ]; then
    echo "   ✓ service-account-key.json found"
else
    echo "   ✗ service-account-key.json not found (needed for Speech-to-Text)"
fi
echo ""

echo "======================================"
echo "Diagnostics complete!"
echo "======================================"
echo ""
echo "Common fixes:"
echo "  - Virtual env not activated: source venv/bin/activate"
echo "  - Missing packages: pip install -r requirements.txt"
echo "  - Missing Vosk model: ./scripts/download_model.sh"
echo "  - Missing Piper (RPi): ./scripts/setup_piper.sh"
echo "  - Audio not working: run 'arecord -l' to check devices, update AUDIO_INPUT_DEVICE_INDEX"
echo ""
