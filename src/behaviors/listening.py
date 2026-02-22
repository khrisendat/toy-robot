import logging
import py_trees
from src.services.api import WakeWordDetector, Listener

logger = logging.getLogger(__name__)

class ListenForWakeWord(py_trees.behaviour.Behaviour):
    def __init__(self, name="ListenForWakeWord"):
        super(ListenForWakeWord, self).__init__(name)
        self.wake_word_detector = WakeWordDetector()

    def update(self):
        self.wake_word_detector.wait_for_wake_word()
        return py_trees.common.Status.SUCCESS


class ListenForCommand(py_trees.behaviour.Behaviour):
    def __init__(self, name="ListenForCommand"):
        super(ListenForCommand, self).__init__(name)
        self.blackboard = self.attach_blackboard_client()
        self.blackboard.register_key(key="command_audio", access=py_trees.common.Access.WRITE)
        self.listener = Listener()

    def update(self):
        for attempt in range(3):
            if attempt > 0:
                logger.info(f"Didn't catch that. Listening again... (attempt {attempt + 1}/3)")
            command = self.listener.listen()
            if command is not None:
                self.blackboard.command_audio = command
                return py_trees.common.Status.SUCCESS
        logger.warning("No command heard after 3 attempts. Going back to wake word.")
        return py_trees.common.Status.FAILURE
