# Backlog

## Refactoring

- **Deduplicate entry points** — `conversation_loop`, `say`, `run`, and `sanitize_for_speech` are copy-pasted between `main_mac.py` and `main_pi.py`. Extract shared logic into a module; entry points should only wire up hardware.

- **Hardware interfaces** — `Speaker`, `MacOSSpeaker`, `Listener`, `MacOSListener`, `Camera`, `MacOSCamera` have no base class or protocol. Define a minimal interface for each so platform swaps are safe and the compiler can catch mismatches.

- **Camera tool wiring** — `make_camera_tool` is appended to `CHILD_ROBOT_CONFIG.tools` manually in each entry point. Move this into the config definition so it's declared once.
