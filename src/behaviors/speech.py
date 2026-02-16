import py_trees
from src.hardware.speaker import Speaker

class Speak(py_trees.behaviour.Behaviour):
    def __init__(self, name="Speak"):
        super(Speak, self).__init__(name)
        self.blackboard = self.attach_blackboard_client()
        # Read the response_text key instead of the old greeting_message
        self.blackboard.register_key(key="response_text", access=py_trees.common.Access.READ)
        self.speaker = Speaker()

    def update(self):
        # Get the message from the correct blackboard variable
        message = self.blackboard.response_text
        self.speaker.say(message)
        return py_trees.common.Status.SUCCESS

    def terminate(self, new_status):
        if self.speaker:
            del self.speaker
            self.speaker = None
