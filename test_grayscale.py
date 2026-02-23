"""
Quick test for the grayscale cliff-detection sensor.

Run with:
    python test_grayscale.py

Hold the robot over a normal surface, then slowly move it to an edge
to see how the readings change. Press Ctrl+C to stop.
"""
import time
from src.hardware.grayscale import GrayscaleSensor, CLIFF_THRESHOLD

sensor = GrayscaleSensor()

if not sensor._available:
    print("Sensor not available — check wiring and robot_hat installation.")
    exit(1)

print(f"Cliff threshold: {CLIFF_THRESHOLD}")
print(f"{'Left':>8}  {'Middle':>8}  {'Right':>8}  {'Cliff?':>8}")
print("-" * 44)

try:
    while True:
        values = sensor.read()
        if values is None:
            print("Read failed.")
        else:
            cliff = sensor.is_cliff(values=values)
            flag = "*** CLIFF ***" if cliff else "OK"
            print(f"{values[0]:>8}  {values[1]:>8}  {values[2]:>8}  {flag}")
        time.sleep(0.3)
except KeyboardInterrupt:
    print("\nDone.")
