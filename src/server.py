import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .lib.robot_memory import RobotMemory
from .lib.robot_session import RobotSession
from .services import (
    tools as _tools,  # noqa: F401 — registers static tools into configs
)
from .services.conversation import CHILD_ROBOT_CONFIG, ConversationManager
from .services.tools import make_camera_tool

logger = logging.getLogger(__name__)


def create_app(camera=None, speaker=None) -> FastAPI:
    app = FastAPI()

    memory = RobotMemory()

    if camera is not None:
        if not any(t.name == "capture_image" for t in CHILD_ROBOT_CONFIG.tools):
            CHILD_ROBOT_CONFIG.tools.append(make_camera_tool(camera.capture_jpeg, media_store=memory))

    llm = ConversationManager(cfg=CHILD_ROBOT_CONFIG, memory=memory)

    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/")
    async def root():
        return FileResponse("static/index.html")

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        logger.info("Browser connected")

        session = RobotSession(llm, memory, speaker)
        await websocket.send_json({"type": "state", "state": "sleeping"})

        try:
            while True:
                msg = await websocket.receive_json()
                async for reply in session.handle(msg):
                    await websocket.send_json(reply)
        except WebSocketDisconnect:
            logger.info("Browser disconnected")

    return app
