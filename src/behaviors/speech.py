import py_trees
from src.hardware.speaker import Speaker
import re

def remove_emojis(text):
    """
    Removes emoji characters from a string.
    """
    # Comprehensive regex to find most emojis
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub(r"", text)

class Speak(py_trees.behaviour.Behaviour):
    def __init__(self, name="Speak"):
        super(Speak, self).__init__(name)
        self.blackboard = self.attach_blackboard_client()
        # Read the response_text key
        self.blackboard.register_key(key="response_text", access=py_trees.common.Access.READ)
        self.speaker = Speaker()

    def update(self):
        # Get the message from the blackboard
        message = self.blackboard.response_text
        # Clean the message to remove emojis before speaking
        cleaned_message = remove_emojis(message).strip()
        self.speaker.say(cleaned_message)
        return py_trees.common.Status.SUCCESS
