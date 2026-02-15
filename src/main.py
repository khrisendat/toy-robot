import py_trees
from behaviors.listening import ListenForWakeWord
from behaviors.generation import GetGreeting
from behaviors.speech import Speak

def create_root():
    root = py_trees.composites.Sequence("RobotRoot")
    
    wake_and_greet = py_trees.composites.Sequence("WakeAndGreet")
    wake_and_greet.add_children([ListenForWakeWord(), GetGreeting(), Speak()])
    
    root.add_child(wake_and_greet)
    
    return root

def main():
    py_trees.logging.level = py_trees.logging.Level.DEBUG
    
    root = create_root()
    tree = py_trees.trees.BehaviourTree(root)
    
    try:
        tree.tick_tock(
            500, 
            py_trees.trees.CONTINUOUS_TICK_TOCK, 
            None, 
            None
        )
    except KeyboardInterrupt:
        tree.interrupt()

if __name__ == '__main__':
    main()
