#!/bin/bash
# This script downloads and sets up the Vosk small English model in a namespaced directory.

MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
ZIP_FILE="vosk-model.zip"
EXTRACTED_DIR_NAME="vosk-model-small-en-us-0.15"
MODELS_ROOT="models"
FINAL_DIR_NAME="$MODELS_ROOT/vosk"

# Create the root models directory if it doesn't exist
mkdir -p "$MODELS_ROOT"

# Check if the model directory already exists
if [ -d "$FINAL_DIR_NAME" ]; then
    echo "Model directory '$FINAL_DIR_NAME' already exists. Skipping download."
    exit 0
fi

echo "Downloading Vosk model..."
curl -L "$MODEL_URL" -o "$ZIP_FILE"

echo "Unzipping model..."
unzip "$ZIP_FILE"

echo "Renaming and moving model directory..."
mv "$EXTRACTED_DIR_NAME" "$FINAL_DIR_NAME"

echo "Cleaning up..."
rm "$ZIP_FILE"

echo "Vosk model setup complete. Model is at '$FINAL_DIR_NAME'."
