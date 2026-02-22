#!/bin/bash
# This script downloads and sets up Piper TTS on a Raspberry Pi.
# Piper is used for local, offline text-to-speech synthesis.

set -e  # Exit on any error

PIPER_DIR="/home/whoopsie/piper"
PIPER_VERSION="1.2.0"
MODEL_NAME="en_GB-alan-low"
HF_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/low"

echo "Setting up Piper TTS..."

# Support --clean flag to wipe and reinstall from scratch
if [ "${1}" = "--clean" ]; then
    echo "Removing existing Piper installation at $PIPER_DIR..."
    rm -rf "$PIPER_DIR"
fi

mkdir -p "$PIPER_DIR"
cd "$PIPER_DIR"

# Download Piper binary if not already present
if [ -f "$PIPER_DIR/piper" ]; then
    echo "Piper binary already exists at $PIPER_DIR/piper. Skipping download."
else
    echo "Downloading Piper v${PIPER_VERSION} for ARM64..."
    wget -4 --show-progress "https://github.com/rhasspy/piper/releases/download/v${PIPER_VERSION}/piper_arm64.tar.gz"

    echo "Extracting Piper..."
    tar xzf piper_arm64.tar.gz
    # The tar extracts to a piper/ subdirectory — move contents up
    if [ -d "$PIPER_DIR/piper" ]; then
        mv "$PIPER_DIR/piper/"* "$PIPER_DIR/"
        rmdir "$PIPER_DIR/piper"
    fi
    chmod +x "$PIPER_DIR/piper"

    echo "Cleaning up..."
    rm piper_arm64.tar.gz
fi

# Download voice model if not already present or is empty
if [ -f "$PIPER_DIR/${MODEL_NAME}.onnx" ] && [ -s "$PIPER_DIR/${MODEL_NAME}.onnx" ]; then
    echo "Voice model already exists at $PIPER_DIR/${MODEL_NAME}.onnx. Skipping download."
else
    # Remove empty/partial file if present
    rm -f "$PIPER_DIR/${MODEL_NAME}.onnx" "$PIPER_DIR/${MODEL_NAME}.onnx.json"

    echo "Downloading voice model from Hugging Face (~60MB)..."
    wget -4 --show-progress -O "${MODEL_NAME}.onnx" "${HF_BASE}/${MODEL_NAME}.onnx"
    wget -4 --show-progress -O "${MODEL_NAME}.onnx.json" "${HF_BASE}/${MODEL_NAME}.onnx.json"
fi

echo ""
echo "Piper TTS setup complete!"
echo ""
echo "Piper binary: $PIPER_DIR/piper"
echo "Voice model:  $PIPER_DIR/${MODEL_NAME}.onnx"
echo ""
echo "Test with:"
echo "  echo 'Hello world' | $PIPER_DIR/piper --model $PIPER_DIR/${MODEL_NAME}.onnx --output_raw | aplay -r 22050 -f S16_LE -t raw"
