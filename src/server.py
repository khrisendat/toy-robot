import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .lib.media_store import MediaStore
from .lib.memory_manager import MemoryManager
from .lib.robot_session import RobotSession
from .lib.speaker_id import SpeakerIdentifier
from .services import (
    tools as _tools,  # noqa: F401 — registers static tools into configs
)
from .services.conversation import CHILD_ROBOT_CONFIG, ConversationManager
from .services.tools import make_camera_tool

logger = logging.getLogger(__name__)


def create_app(camera=None, speaker=None) -> FastAPI:
    app = FastAPI()

    memory = MemoryManager()
    speaker_id = SpeakerIdentifier() if SpeakerIdentifier.profiles_exist() else None
    media_store = MediaStore()

    if camera is not None:
        if not any(t.name == "capture_image" for t in CHILD_ROBOT_CONFIG.tools):
            CHILD_ROBOT_CONFIG.tools.append(make_camera_tool(camera.capture_jpeg, media_store=media_store))

    llm = ConversationManager(cfg=CHILD_ROBOT_CONFIG, memory=memory)

    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/")
    async def root():
        return FileResponse("static/index.html")

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        logger.info("Browser connected")

        session = RobotSession(llm, memory, speaker, speaker_id=speaker_id, media_store=media_store)
        await websocket.send_json({"type": "state", "state": "sleeping"})

        try:
            while True:
                msg = await websocket.receive_json()
                async for reply in session.handle(msg):
                    await websocket.send_json(reply)
        except WebSocketDisconnect:
            logger.info("Browser disconnected")

    return app
