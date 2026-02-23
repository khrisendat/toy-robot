"""
Quick test for wheel idle animation.

Run with:
    python test_wheels.py

The robot will wiggle around for 15 seconds then stop.
Press Ctrl+C to stop early.
"""
import time
from src.hardware.wheels import Wheels

wheels = Wheels()

if not wheels._available:
    print("Wheels not available — check picarx installation and wiring.")
    exit(1)

print("Starting idle animation for 15 seconds...")
wheels.idle()

try:
    time.sleep(15)
except KeyboardInterrupt:
    pass

print("Stopping.")
wheels.stop()
print("Done.")
