# Kabir's Robot

This project contains the source code for a robot toy for a four-year-old named Kabir. The robot is built on a Raspberry Pi 5 using the SunFounder PiCar-X kit.

## Architecture

The robot's logic is orchestrated using a behavior tree implemented with the `py_trees` library. The core services, such as wake word detection and LLM interaction, are abstracted from the hardware control layer to ensure future portability to ROS2.

## Getting Started

### System Dependencies

This project relies on some system-level packages that need to be installed separately from the Python requirements.

- **On macOS (with Homebrew):**
  ```bash
  brew install mpg123
  ```

- **On Raspberry Pi (Debian):**
  ```bash
  sudo apt-get update && sudo apt-get install -y mpg123
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

### Running the Robot

To run the robot, execute the `main.py` script from the `src` directory:

```bash
python src/main.py
```

This will start the behavior tree and the robot will begin listening for the wake word.

## Connecting to the Robot

To connect to the Raspberry Pi via SSH, use the following command. The IP address has been set to be static via DHCP reservation.

```bash
ssh whoopsie@192.168.5.9
```

