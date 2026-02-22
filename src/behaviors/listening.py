import py_trees
from src.services.api import WakeWordDetector, Listener

class ListenForWakeWord(py_trees.behaviour.Behaviour):
    def __init__(self, name="ListenForWakeWord"):
        super(ListenForWakeWord, self).__init__(name)
        # Initialize the detector in the constructor
        self.wake_word_detector = WakeWordDetector()

    def update(self):
        self.wake_word_detector.wait_for_wake_word()
        return py_trees.common.Status.SUCCESS

class ListenForCommand(py_trees.behaviour.Behaviour):
    def __init__(self, name="ListenForCommand"):
        super(ListenForCommand, self).__init__(name)
        self.blackboard = self.attach_blackboard_client()
        self.blackboard.register_key(key="command_text", access=py_trees.common.Access.WRITE)
        # Initialize the listener in the constructor
        self.listener = Listener()

    def update(self):
        for attempt in range(3):
            if attempt > 0:
                print(f"Didn't catch that. Listening again... (attempt {attempt + 1}/3)", flush=True)
            command = self.listener.listen()
            if command:
                self.blackboard.command_text = command
                return py_trees.common.Status.SUCCESS
        print("No command heard after 3 attempts. Going back to wake word.", flush=True)
        return py_trees.common.Status.FAILURE
