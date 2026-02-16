"""
Mock services for running the robot in a text-only mode without a microphone.
"""

class MockWakeWordDetector:
    """A mock wake word detector that waits for the user to press Enter."""
    def wait_for_wake_word(self):
        input("Press Enter to simulate wake word detection...")
        print("Wake word detected!")
        return

class MockListener:
    """A mock listener that prompts the user to type a command."""
    def listen(self, duration=5):
        command = input("Please type your command: ")
        print(f"Command received: {command}")
        return command
