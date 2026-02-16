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
        command = self.listener.listen()
        if command:
            self.blackboard.command_text = command
            return py_trees.common.Status.SUCCESS
        else:
            # Return failure if no command was heard, so the tree stops
            return py_trees.common.Status.FAILURE
