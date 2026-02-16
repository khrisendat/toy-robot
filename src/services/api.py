"""
Services API Abstraction Layer.

This module detects if a microphone is available and exports the appropriate
service classes. If a microphone is found, it exports the real audio-based
services. Otherwise, it exports mock services that use the terminal for input.
"""

import pyaudio

def is_microphone_available():
    """Check if any audio input devices are available."""
    pa = pyaudio.PyAudio()
    try:
        info = pa.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        for i in range(0, num_devices):
            if pa.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels') > 0:
                return True
        return False
    except Exception:
        return False
    finally:
        pa.terminate()

if is_microphone_available():
    print("Microphone detected. Using real audio services.")
    from .wake_word import WakeWordDetector
    from .listener import Listener
else:
    print("No microphone detected. Using text-based mock services.")
    from .mock_services import MockWakeWordDetector as WakeWordDetector
    from .mock_services import MockListener as Listener
