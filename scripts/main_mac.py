import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from src.hardware.macos_camera import MacOSCamera
from src.server import create_app

_log_format = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
_log_datefmt = "%H:%M:%S"

logging.basicConfig(level=logging.INFO, format=_log_format, datefmt=_log_datefmt)
_file_handler = logging.FileHandler("mac_conversation.log")
_file_handler.setFormatter(logging.Formatter(_log_format, datefmt=_log_datefmt))
logging.getLogger().addHandler(_file_handler)

if __name__ == "__main__":
    camera = MacOSCamera()
    app = create_app(camera=camera)
    uvicorn.run(app, host="0.0.0.0", port=8000)
