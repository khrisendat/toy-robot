"""
Hardware API Abstraction Layer.

Detects the platform and exports the appropriate hardware classes.
On Raspberry Pi, exports real picarx classes and the Pi-specific Listener.
On macOS/other, exports mock picarx classes and the MacOSListener.
If no microphone is available, falls back to a text-based MockListener.
"""

import platform
import pyaudio

IS_PI = platform.machine().startswith("arm") or platform.machine().startswith("aarch64")

if IS_PI:
    print("Running on Raspberry Pi. Importing real hardware classes.")
    try:
        from picarx import Pin, ADC, PWM, PiCarX
    except ImportError:
        print("Error: picar-x library not found. Please install it using 'pip install picar-x'")
        from .mock_hardware import Pin, ADC, PWM, PiCarX
else:
    print("Not running on Raspberry Pi. Importing mock hardware classes.")
    from .mock_hardware import Pin, ADC, PWM, PiCarX


def _is_microphone_available():
    pa = pyaudio.PyAudio()
    try:
        info = pa.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        for i in range(num_devices):
            if pa.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels') > 0:
                return True
        return False
    except Exception:
        return False
    finally:
        pa.terminate()


if _is_microphone_available():
    if IS_PI:
        print("Microphone detected on Raspberry Pi. Using Pi listener and wake word detector.")
        from .listener import Listener
    else:
        print("Microphone detected on macOS. Using macOS listener and wake word detector.")
        from .macos_listener import MacOSListener as Listener
    from .wake_word import WakeWordDetector
else:
    print("No microphone detected. Using text-based mock listener and wake word detector.")
    from .mock_hardware import MockListener as Listener
    from .mock_hardware import MockWakeWordDetector as WakeWordDetector
