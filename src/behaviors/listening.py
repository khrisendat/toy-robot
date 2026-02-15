import py_trees
from ..services.wake_word import WakeWordDetector

class ListenForWakeWord(py_trees.behaviour.Behaviour):
    def __init__(self, name="ListenForWakeWord"):
        super(ListenForWakeWord, self).__init__(name)
        self.wake_word_detector = None

    def setup(self, **kwargs):
        self.wake_word_detector = WakeWordDetector()

    def update(self):
        self.wake_word_detector.wait_for_wake_word()
        return py_trees.common.Status.SUCCESS

    def terminate(self, new_status):
        if self.wake_word_detector:
            del self.wake_word_detector
