import logging
import py_trees
from src.behaviors.listening import ListenForWakeWord, ListenForCommand
from src.behaviors.generation import GetLLMResponse
from src.behaviors.speech import Speak
from src.behaviors.safety import CheckBattery, CheckCliff
from src.hardware.grayscale import GrayscaleSensor
from src.hardware.speaker import Speaker
from src.hardware.head import Head

_log_format = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
_log_datefmt = "%H:%M:%S"

logging.basicConfig(
    level=logging.DEBUG,
    format=_log_format,
    datefmt=_log_datefmt,
)

_file_handler = logging.FileHandler("robot.log")
_file_handler.setFormatter(logging.Formatter(_log_format, datefmt=_log_datefmt))
logging.getLogger().addHandler(_file_handler)

def create_root(speaker, head, grayscale):
    """
    Creates the root of the behavior tree.
    The tree will repeatedly listen for a wake word, then listen for a command,
    get a response from the LLM, and speak the response.
    """
    # The root is a sequence that will run its children in order.
    # The Selector with a Memory allows the sequence to be re-run in a loop.
    root = py_trees.composites.Selector("RobotRoot", memory=True)

    # Safety guards — run on every tick before the conversation branch.
    # Each returns SUCCESS (blocking conversation) if a hazard is detected.
    battery_check = CheckBattery(speaker=speaker)
    cliff_check = CheckCliff(speaker=speaker, grayscale=grayscale)

    # This is the main conversational sequence
    conversation_sequence = py_trees.composites.Sequence("Conversation", memory=False)
    conversation_sequence.add_children([
        ListenForWakeWord(head=head),
        ListenForCommand(head=head),
        GetLLMResponse(),
        Speak(speaker=speaker, head=head)
    ])

    root.add_children([battery_check, cliff_check, conversation_sequence])
    
    return root

def main():
    # Set up logging to see the tree's behavior
    py_trees.logging.level = py_trees.logging.Level.DEBUG
    
    speaker = Speaker()
    head = Head()
    grayscale = GrayscaleSensor()
    root = create_root(speaker, head, grayscale)
    tree = py_trees.trees.BehaviourTree(root)

    logging.getLogger(__name__).info("Starting robot...")
    from src import config
    speaker.say(f"Hey {config.CHILD_NAME}! I'm awake!")

    try:
        tree.tick_tock(period_ms=500)
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Robot shutting down...")
        tree.interrupt()

if __name__ == '__main__':
    main()
