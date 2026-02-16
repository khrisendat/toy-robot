#!/bin/bash
# This script downloads and sets up Piper TTS on a Raspberry Pi.
# Piper is used for local, offline text-to-speech synthesis.

set -e  # Exit on any error

PIPER_DIR="/home/whoopsie/piper"
PIPER_VERSION="1.2.0"

echo "Setting up Piper TTS..."

# Create the Piper directory
mkdir -p "$PIPER_DIR"
cd "$PIPER_DIR"

# Check if Piper binary already exists
if [ -f "$PIPER_DIR/piper" ]; then
    echo "Piper binary already exists at $PIPER_DIR/piper. Skipping download."
else
    echo "Downloading Piper v${PIPER_VERSION} for ARM64..."
    wget -q --show-progress "https://github.com/rhasspy/piper/releases/download/v${PIPER_VERSION}/piper_arm64.tar.gz"
    
    echo "Extracting Piper..."
    tar xzf piper_arm64.tar.gz
    
    # Make the binary executable
    chmod +x piper
    
    echo "Cleaning up..."
    rm piper_arm64.tar.gz
fi

# Check if voice model already exists
if [ -f "$PIPER_DIR/en_GB-alan-low.onnx" ]; then
    echo "Voice model already exists at $PIPER_DIR/en_GB-alan-low.onnx. Skipping download."
else
    echo "Downloading English voice model..."
    wget -q --show-progress "https://github.com/rhasspy/piper/releases/download/v${PIPER_VERSION}/voice-en_GB-alan-low.tar.gz"
    
    echo "Extracting voice model..."
    tar xzf voice-en_GB-alan-low.tar.gz
    
    echo "Cleaning up..."
    rm voice-en_GB-alan-low.tar.gz
fi

echo ""
echo "✓ Piper TTS setup complete!"
echo ""
echo "Piper binary: $PIPER_DIR/piper"
echo "Voice model: $PIPER_DIR/en_GB-alan-low.onnx"
echo ""
echo "You can test Piper with:"
echo "  echo 'Hello world' | $PIPER_DIR/piper --model $PIPER_DIR/en_GB-alan-low.onnx --output_raw | aplay -D default -r 22050 -f S16_LE -t raw"
