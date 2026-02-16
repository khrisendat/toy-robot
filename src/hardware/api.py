"""
Hardware API Abstraction Layer.

This module detects the underlying operating system and exports the appropriate
hardware control classes. For a Raspberry Pi, it will export the real `picarx`
classes. For any other OS (like macOS or Windows), it will export mock classes
that simulate the hardware for local development and testing.
"""

import platform

# Check if we are running on a Raspberry Pi by checking the processor architecture
IS_PI = platform.machine().startswith("arm") or platform.machine().startswith("aarch64")

if IS_PI:
    print("Running on Raspberry Pi. Importing real hardware classes.")
    try:
        from picarx import Pin, ADC, PWM, PiCarX
    except ImportError:
        print("Error: picar-x library not found. Please install it using 'pip install picar-x'")
        # Provide dummy classes to prevent crashing the whole application if the import fails
        from .mock_hardware import Pin, ADC, PWM, PiCarX
else:
    print("Not running on Raspberry Pi. Importing mock hardware classes.")
    from .mock_hardware import Pin, ADC, PWM, PiCarX

# You can add any other hardware classes here following the same pattern.
