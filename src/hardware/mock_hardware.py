"""
Mock hardware classes for running the robot code on a non-Raspberry Pi machine.
These classes mimic the interface of the picar-x library but simply print
actions to the console instead of controlling physical hardware.
"""

class Pin:
    """A mock Pin class."""
    def __init__(self, pin_name):
        self.pin_name = pin_name
        print(f"MockPin: Initialized pin {self.pin_name}")

class ADC:
    """A mock ADC class."""
    def __init__(self, channel):
        self.channel = channel
        print(f"MockADC: Initialized ADC on channel {self.channel}")

    def read(self):
        print("MockADC: Reading value.")
        return 0 # Return a dummy value

class PWM:
    """A mock PWM class."""
    def __init__(self, channel):
        self.channel = channel
        print(f"MockPWM: Initialized PWM on channel {self.channel}")

    def prescale(self, value):
        print(f"MockPWM: Setting prescale to {value}")

    def period(self, value):
        print(f"MockPWM: Setting period to {value}")

    def pulse_width_percent(self, value):
        print(f"MockPWM: Setting pulse width to {value}%")

class PiCarX:
    """A mock PiCarX class."""
    def __init__(self):
        print("MockPiCarX: Initialized.")

    def set_motor_speed(self, motor, speed):
        print(f"MockPiCarX: Setting motor {motor} speed to {speed}")

    def set_dir_servo_angle(self, angle):
        print(f"MockPiCarX: Steering angle {angle}")

    def forward(self, speed):
        print(f"MockPiCarX: Moving forward at speed {speed}")

    def backward(self, speed):
        print(f"MockPiCarX: Moving backward at speed {speed}")

    def stop(self):
        print("MockPiCarX: Stopping motors.")
