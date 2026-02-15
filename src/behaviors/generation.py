import py_trees

class GetGreeting(py_trees.behaviour.Behaviour):
    def __init__(self, name="GetGreeting"):
        super(GetGreeting, self).__init__(name)
        self.blackboard = self.attach_blackboard_client()
        self.blackboard.register_key(key="greeting_message", access=py_trees.common.Access.WRITE)

    def update(self):
        self.blackboard.greeting_message = "Hello Kabir!"
        return py_trees.common.Status.SUCCESS
