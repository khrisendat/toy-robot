import py_trees
from src.services.llm import LLMClient

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
        self.blackboard.register_key(key="command_text", access=py_trees.common.Access.READ)
        self.blackboard.register_key(key="response_text", access=py_trees.common.Access.WRITE)
        self.llm_client = LLMClient()

    def update(self):
        prompt = self.blackboard.command_text
        # Add a simple system prompt for context
        full_prompt = f"You are a friendly robot assistant for a four-year-old named Kabir. Be kind, simple, and creative. The user said: {prompt}"
        response = self.llm_client.generate_response(full_prompt)
        self.blackboard.response_text = response
        return py_trees.common.Status.SUCCESS
