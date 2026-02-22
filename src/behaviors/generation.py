import py_trees
from src.services.llm import LLMClient
from src.hardware.camera import Camera

class GetGreeting(py_trees.behaviour.Behaviour):
    def __init__(self, name="GetGreeting"):
        super(GetGreeting, self).__init__(name)
        self.blackboard = self.attach_blackboard_client()
        self.blackboard.register_key(key="greeting_message", access=py_trees.common.Access.WRITE)

    def update(self):
        self.blackboard.greeting_message = "Hello Kabir!"
        return py_trees.common.Status.SUCCESS

class GetLLMResponse(py_trees.behaviour.Behaviour):
    def __init__(self, name="GetLLMResponse"):
        super(GetLLMResponse, self).__init__(name)
        self.blackboard = self.attach_blackboard_client()
        self.blackboard.register_key(key="command_audio", access=py_trees.common.Access.READ)
        self.blackboard.register_key(key="response_text", access=py_trees.common.Access.WRITE)
        self.llm_client = LLMClient()
        self.camera = Camera()

    def update(self):
        response = self.llm_client.generate_response(self.blackboard.command_audio, get_image=self.camera.capture_jpeg)
        self.blackboard.response_text = response
        return py_trees.common.Status.SUCCESS
