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
        return pa.get_device_count() > 0 and pa.get_default_input_device_info() is not None
    except IOError:
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
