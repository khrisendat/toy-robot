# Kabir's Robot

This project contains the source code for a robot toy for a four-year-old named Kabir. The robot is built on a Raspberry Pi 5 using the SunFounder PiCar-X kit.

## Architecture

The robot's logic is orchestrated using a behavior tree implemented with the `py_trees` library. The core services, such as wake word detection and LLM interaction, are abstracted from the hardware control layer to ensure future portability to ROS2.

## Getting Started

### System Dependencies

This project relies on some system-level packages and SDKs that need to be installed and configured before installing the Python requirements.

#### 1. Audio Playback & Recording

- **On macOS (with Homebrew):**
  Install `mpg123` for audio playback and `portaudio` for microphone access.
  ```bash
  brew install mpg123 portaudio
  ```

- **On Raspberry Pi (Debian):**
  Install `mpg123` and the `portaudio` development libraries.
  ```bash
  sudo apt-get update && sudo apt-get install -y mpg123 libportaudio-dev
  ```
  **Troubleshooting Audio Input:**
  If the robot doesn't respond to voice commands, you might need to explicitly set the audio input device index. Run `arecord -l` on your Raspberry Pi to list available capture devices. Look for your microphone (e.g., "USB PnP Sound Device") and note its `card` number (e.g., `card 3`). Then, update the `input_device_index` in `src/services/wake_word.py` and `src/services/listener.py` to match this number.

#### 2. Google Cloud Authentication

The robot uses Google Cloud for Text-to-Speech and Speech-to-Text. Authentication is handled via a Service Account Key.

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
*   A Gemini API Key for LLM interaction.

### Vosk Model Installation

This project uses the Vosk library for offline wake word detection. A small language model is required. A script is provided to automate the download and setup into a `models/vosk` directory.

From the root of the `toy_robot` project directory, run:
```bash
./scripts/download_model.sh
```

### Installation

1.  Clone the repository:
    ```bash
    git clone <repository_url>
    ```
2.  Navigate to the `toy_robot` directory:
    ```bash
    cd kabir_robot
    ```
3.  Create a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
4.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
5.  Create a `.env` file in the `toy_robot` directory and add your API key:
    ```
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    ```

### Hardware-Specific Installation (Raspberry Pi Only)

To control the robot's motors and servos, the `picar-x` library is required. This library only works on a Raspberry Pi. After setting up the main environment, install it with pip:

```bash
pip install picar-x
```

### Running the Robot

To run the robot, execute the `main.py` script from the project's root directory:

```bash
python3 main.py
```

This will start the behavior tree and the robot will begin listening for the wake word.

## Connecting to the Robot

To connect to the Raspberry Pi via SSH, use the following command. The IP address has been set to be static via DHCP reservation.

```bash
ssh whoopsie@192.168.5.9
```

