import logging
import os
import sys

# Re-exec under python3.11 with the correct libexpat if not already there.
# Homebrew Python 3.11 links against a newer libexpat than the macOS system one.
_EXPAT = "/opt/homebrew/opt/expat/lib"
if sys.version_info < (3, 11) or _EXPAT not in os.environ.get("DYLD_LIBRARY_PATH", ""):
    _py311 = "/opt/homebrew/bin/python3.11"
    if os.path.exists(_py311):
        env = os.environ.copy()
        env["DYLD_LIBRARY_PATH"] = _EXPAT + ":" + env.get("DYLD_LIBRARY_PATH", "")
        os.execve(_py311, [_py311] + sys.argv, env)

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "memorylib", "src"))

import uvicorn  # noqa: E402

from src.hardware.kokoro_speaker import KokoroSpeaker  # noqa: E402
from src.hardware.macos_camera import MacOSCamera  # noqa: E402
from src.server import create_app  # noqa: E402

_log_format = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
_log_datefmt = "%H:%M:%S"

logging.basicConfig(level=logging.INFO, format=_log_format, datefmt=_log_datefmt)
_file_handler = logging.FileHandler("mac_conversation.log")
_file_handler.setFormatter(logging.Formatter(_log_format, datefmt=_log_datefmt))
logging.getLogger().addHandler(_file_handler)

if __name__ == "__main__":
    camera = MacOSCamera()
    speaker = KokoroSpeaker()
    app = create_app(camera=camera, speaker=speaker)
    uvicorn.run(app, host="0.0.0.0", port=8000)
