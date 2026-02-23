# Kabir's Robot

A voice-driven robot companion for a four-year-old, built on a Raspberry Pi 5 using the SunFounder PiCar-X kit.

## Architecture

The robot runs as a set of concurrent async tasks orchestrated with Python's `asyncio`:

- **`conversation_loop`** — waits for the wake word "hey robot", listens for a command, sends audio to Gemini for a response, and speaks it back. Repeats forever.
- **`safety_monitor`** — checks battery voltage and cliff sensors every second, independent of whatever the conversation loop is doing. Speaks warnings when needed.

Adding new capabilities (movement, expressions, etc.) means adding a new task to `asyncio.gather()`.

### Key components

| Path | What it does |
|---|---|
| `main.py` | Async orchestration — conversation loop, safety monitor |
| `src/hardware/speaker.py` | Piper TTS (persistent process, offline) |
| `src/hardware/head.py` | Pan/tilt servo animations (idle, listening, speaking) |
| `src/hardware/camera.py` | Pi Camera JPEG capture for vision requests |
| `src/hardware/grayscale.py` | Cliff/edge detection via grayscale sensor array |
| `src/services/wake_word.py` | Vosk-based "hey robot" wake word detection |
| `src/services/listener.py` | Microphone recording with silence detection |
| `src/services/llm.py` | Gemini multimodal API (audio + optional image) |

### How vision works

Gemini processes the audio directly (no separate STT step). If the child asks to look at something, Gemini returns a special signal and the robot captures a JPEG from the Pi Camera and makes a second API call with the image.

---

## Getting Started

### Prerequisites

- Python 3.8+
- A Gemini API key — [aistudio.google.com](https://aistudio.google.com)
- Raspberry Pi OS with `picamera2` installed (comes pre-installed)
- Piper TTS binary and voice model (see below)

### System dependencies

```bash
sudo apt-get update && sudo apt-get install -y alsa-utils libportaudio-dev
```

### Installation

1. **Clone the repo:**
   ```bash
   git clone <repository_url>
   cd toy-robot
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv --system-site-packages venv
   source venv/bin/activate
   ```
   > `--system-site-packages` is required so the venv can access `picamera2`, which is installed at the system level on Raspberry Pi OS.

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Download the Vosk wake word model:**
   ```bash
   chmod +x scripts/download_model.sh && ./scripts/download_model.sh
   ```

5. **Set up Piper TTS:**
   ```bash
   chmod +x scripts/setup_piper.sh && ./scripts/setup_piper.sh
   ```
   This installs Piper to `/home/whoopsie/piper/` with the `en_GB-alan-low` voice. Override with env vars if needed:
   ```
   PIPER_BINARY=/path/to/piper
   PIPER_MODEL=/path/to/model.onnx
   ```

6. **Create a `.env` file:**
   ```
   GEMINI_API_KEY=your_key_here
   AUDIO_INPUT_DEVICE_INDEX=2
   CHILD_NAME=Kabir
   ```
   Run `arecord -l` to find your microphone's device index.

### Running

```bash
source venv/bin/activate
python main.py
```

The robot will say "Hey Kabir! I'm awake!" and start listening for "hey robot".

Logs are written to both stdout and `robot.log`.

---

## Connecting to the robot

```bash
ssh whoopsie@192.168.4.138
```

---

## Troubleshooting

**Finding your audio device index:**
```bash
arecord -l
```
Look for your USB microphone and use its card number in `AUDIO_INPUT_DEVICE_INDEX`.

**Checking live sensor readings:**
```bash
python test_grayscale.py
```
Hold the robot over a flat surface, then near an edge to verify cliff detection.

**Robot isn't responding to wake word:**
Make sure the Vosk model is downloaded (`models/vosk/` should exist) and `AUDIO_INPUT_DEVICE_INDEX` points to the right device.

**Camera not working:**
Ensure the venv was created with `--system-site-packages` and the Pi Camera is enabled in `raspi-config`.
