import py_trees
from behaviors.listening import ListenForWakeWord, ListenForCommand
from behaviors.generation import GetLLMResponse
from behaviors.speech import Speak

def create_root():
    """
    Creates the root of the behavior tree.
    The tree will repeatedly listen for a wake word, then listen for a command,
    get a response from the LLM, and speak the response.
    """
    # The root is a sequence that will run its children in order.
    # The Selector with a Memory allows the sequence to be re-run in a loop.
    root = py_trees.composites.Selector("RobotRoot", memory=True)

    # This is the main conversational sequence
    conversation_sequence = py_trees.composites.Sequence("Conversation")
    conversation_sequence.add_children([
        ListenForWakeWord(),
        ListenForCommand(),
        GetLLMResponse(),
        Speak()
    ])

    # The root's only child is the conversation sequence.
    # Because the root is a Selector with memory, after the sequence finishes,
    # it will be reset and the tree will tick it again on the next cycle,
    # effectively creating an infinite loop.
    root.add_child(conversation_sequence)
    
    return root

def main():
    # Set up logging to see the tree's behavior
    py_trees.logging.level = py_trees.logging.Level.DEBUG
    
    root = create_root()
    tree = py_trees.trees.BehaviourTree(root)
    
    print("Starting robot...")
    
    try:
        # Tick the tree continuously
        tree.tick_tock(
            period_ms=500,  # Tick every 500 milliseconds
        )
    except KeyboardInterrupt:
        # Gracefully shut down on Ctrl+C
        print("Robot shutting down...")
        tree.interrupt()

if __name__ == '__main__':
    main()
