import py_trees
from ..hardware.speaker import Speaker

class Speak(py_trees.behaviour.Behaviour):
    def __init__(self, name="Speak"):
        super(Speak, self).__init__(name)
        self.blackboard = self.attach_blackboard_client()
        self.blackboard.register_key(key="greeting_message", access=py_trees.common.Access.READ)
        self.speaker = None

    def setup(self, **kwargs):
        self.speaker = Speaker()

    def update(self):
        message = self.blackboard.greeting_message
        self.speaker.say(message)
        return py_trees.common.Status.SUCCESS
