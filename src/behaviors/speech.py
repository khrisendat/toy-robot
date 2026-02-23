import py_trees
import re

def sanitize_for_speech(text):
    """Remove characters that TTS cannot speak meaningfully."""
    # Remove emojis
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub("", text)
    # Remove other unspeakable characters: *, #, _, ~, `, |, <, >, ^
    text = re.sub(r"[*#_~`|<>^]", "", text)
    # Collapse extra whitespace left behind
    text = re.sub(r" +", " ", text)
    return text.strip()

class Speak(py_trees.behaviour.Behaviour):
    def __init__(self, speaker, head=None, name="Speak"):
        super(Speak, self).__init__(name)
        self.blackboard = self.attach_blackboard_client()
        self.blackboard.register_key(key="response_text", access=py_trees.common.Access.READ)
        self.speaker = speaker
        self.head = head

    def update(self):
        message = self.blackboard.response_text
        cleaned_message = sanitize_for_speech(message)
        if self.head:
            self.head.speaking()
        self.speaker.say(cleaned_message)
        if self.head:
            self.head.center()
        return py_trees.common.Status.SUCCESS
