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

#### 2. Google Cloud SDK

The robot uses Google Cloud for Text-to-Speech and Speech-to-Text, which requires authentication.

- **On macOS (with Homebrew):**
  1. Install the SDK:
     ```bash
     brew install --cask google-cloud-sdk
     ```
  2. Initialize the SDK. This will open a browser to log you in.
     ```bash
     gcloud init
     ```
  3. Set up application default credentials:
     ```bash
     gcloud auth application-default login
     ```

- **On Raspberry Pi (Debian):**
  1. Run the interactive installer:
     ```bash
     curl -sSL https://sdk.cloud.google.com | bash
     ```
  2. Restart your shell or run `source ~/.bashrc`.
  3. Initialize the SDK.
     ```bash
     gcloud init
     ```
  4. Set up application default credentials. This will provide a URL to open in a browser on your main computer.
     ```bash
     gcloud auth application-default login
     ```

### Prerequisites

*   Python 3.8+
*   A Gemini API Key for LLM interaction.

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
5.  Create a `.env` file in the `toy_robot` directory and add your API keys:
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

