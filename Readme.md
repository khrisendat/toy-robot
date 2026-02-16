# Kabir's Robot

This project contains the source code for a robot toy for a four-year-old named Kabir. The robot is built on a Raspberry Pi 5 using the SunFounder PiCar-X kit.

## Architecture

The robot's logic is orchestrated using a behavior tree implemented with the `py_trees` library. The core services, such as wake word detection and LLM interaction, are abstracted from the hardware control layer to ensure future portability to ROS2.

## Getting Started

### System Dependencies

This project relies on some system-level packages and SDKs that need to be installed and configured before installing the Python requirements.

#### 1. Audio Playback & Recording

- **On macOS (with Homebrew):**
  Install `portaudio` for microphone access.
  ```bash
  brew install portaudio
  ```

- **On Raspberry Pi (Debian):**
  Install `portaudio` development libraries and `alsa-utils` for audio tools.
  ```bash
  sudo apt-get update && sudo apt-get install -y alsa-utils libportaudio-dev
  ```
  **Troubleshooting Audio Input:**
  If the robot doesn't respond to voice commands, you might need to explicitly set the audio input device index. Run `arecord -l` on your Raspberry Pi to list available capture devices. Look for your microphone (e.g., "USB PnP Sound Device") and note its `card` number (e.g., `card 3`). Then, update the `AUDIO_INPUT_DEVICE_INDEX` in your `.env` file:
  ```
  AUDIO_INPUT_DEVICE_INDEX=3
  ```
  
  **Note on Audio Channels:**
  USB audio devices typically require stereo (2-channel) input, even if you're only using one microphone. The code automatically converts stereo input to mono for speech processing.

#### 2. Piper Text-to-Speech (Raspberry Pi Only)

The robot uses Piper for offline text-to-speech synthesis. This provides fast, natural-sounding speech without cloud API calls.

1. **Download and Install Piper:**
   ```bash
   cd /home/whoopsie
   wget https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_arm64.tar.gz
   tar xzf piper_arm64.tar.gz
   ```

2. **Download a Voice Model:**
   ```bash
   cd /home/whoopsie/piper
   wget https://github.com/rhasspy/piper/releases/download/v1.2.0/voice-en_GB-alan-low.tar.gz
   tar xzf voice-en_GB-alan-low.tar.gz
   ```

3. **Set Environment Variables (Optional):**
   Add to your `.env` file if Piper is installed in a different location:
   ```
   PIPER_BINARY=/path/to/piper
   PIPER_MODEL=/path/to/model.onnx
   ```
   Default paths are `/home/whoopsie/piper/piper` and `/home/whoopsie/piper/en_GB-alan-low.onnx`.

#### 3. Google Cloud Authentication

The robot uses Google Cloud for Speech-to-Text recognition. Authentication is handled via a Service Account Key.

1.  **Create a Service Account:**
    - Go to the [Google Cloud Console Service Accounts page](https://console.cloud.google.com/iam-admin/serviceaccounts).
    - Select your project.
    - Click **"+ CREATE SERVICE ACCOUNT"**, give it a name (e.g., `toy-robot-sa`), and click **"CREATE AND CONTINUE"**.
    - Grant it the **"Project" > "Editor"** role, then click **"CONTINUE"** and **"DONE"**.
2.  **Create and Download a Key:**
    - Find your new service account in the list, click the three dots under "Actions", and select **"Manage keys"**.
    - Click **"ADD KEY" > "Create new key"**.
    - Choose **"JSON"** and click **"CREATE"**. A JSON file will be downloaded.
3.  **Add Key to Project:**
    - Rename the downloaded file to `service-account-key.json`.
    - Move it to the root of the `toy_robot` project directory. The `.gitignore` file is already configured to ignore this file.

### Prerequisites

*   Python 3.8+
*   A Gemini API Key for LLM interaction
*   (Raspberry Pi only) Piper TTS binary and voice model
*   (Raspberry Pi only) Google Cloud service account key for Speech-to-Text

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd toy_robot
   ```

2. **Quick setup on Raspberry Pi (Recommended):**
   Run the automated setup script to install all dependencies and download models:
   ```bash
   chmod +x scripts/setup_rpi.sh
   ./scripts/setup_rpi.sh
   ```
   Then update your `.env` file with your Gemini API key and audio device index.

3. **Manual installation (if not using setup script):**
   
   a. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
   
   b. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   
   c. Download the Vosk wake word model:
   ```bash
   chmod +x scripts/download_model.sh
   ./scripts/download_model.sh
   ```
   
   d. Set up Piper TTS:
   ```bash
   chmod +x scripts/setup_piper.sh
   ./scripts/setup_piper.sh
   ```
   
   e. Create a `.env` file in the root of the project:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   AUDIO_INPUT_DEVICE_INDEX=3
   ```

4. **Find your audio device index:**
   Run `arecord -l` to list your audio devices, then update `AUDIO_INPUT_DEVICE_INDEX` in `.env`

5. **Set up Google Cloud (for Speech-to-Text):**
   - Create a service account in Google Cloud Console
   - Download the JSON key file
   - Rename it to `service-account-key.json`
   - Place it in the root of the `toy_robot` directory

6. **Hardware-specific setup (Raspberry Pi only):**
   To control the robot's motors and servos, install the `picar-x` library:
   ```bash
   pip install picar-x
   ```

### Available Scripts

The `scripts/` directory contains helpful utilities:

- **`setup_rpi.sh`** - Automated setup for Raspberry Pi (runs all steps below)
- **`download_model.sh`** - Downloads the Vosk wake word model
- **`setup_piper.sh`** - Downloads and sets up Piper TTS
- **`diagnose.sh`** - Checks your setup and troubleshoots issues
- **`example_chat.py`** - Example of a simple chat interface (reference)

To make any script executable and run it:
```bash
chmod +x scripts/script_name.sh
./scripts/script_name.sh
```

### Troubleshooting

If you encounter issues, run the diagnostics script:
```bash
chmod +x scripts/diagnose.sh
./scripts/diagnose.sh
```

This will check:
- Python installation and virtual environment
- Required Python packages
- Vosk and Piper models
- Audio devices
- Environment configuration

### Running the Robot

To run the robot, execute the `main.py` script from the project's root directory:

```bash
python3 main.py
```

This will start the behavior tree and the robot will begin listening for the wake word "hey robot".

## Connecting to the Robot

To connect to the Raspberry Pi via SSH, use the following command. The IP address has been set to be static via DHCP reservation.

```bash
ssh whoopsie@192.168.5.9
```

