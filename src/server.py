import asyncio
import base64
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .lib.memory import MemoryStore
from .lib.speech import sanitize_for_speech
from .services import (
    tools as _tools,  # noqa: F401 — registers static tools into configs
)
from .services.conversation import CHILD_ROBOT_CONFIG, ConversationManager
from .services.tools import make_camera_tool

logger = logging.getLogger(__name__)


def create_app(camera=None, speaker=None) -> FastAPI:
    app = FastAPI()

    memory = MemoryStore()

    if camera is not None:
        if not any(t.name == "capture_image" for t in CHILD_ROBOT_CONFIG.tools):
            CHILD_ROBOT_CONFIG.tools.append(make_camera_tool(camera.capture_jpeg))

    llm = ConversationManager(cfg=CHILD_ROBOT_CONFIG, memory=memory)

    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/")
    async def root():
        return FileResponse("static/index.html")

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        logger.info("Browser connected")
        busy = False
        await websocket.send_json({"type": "state", "state": "idle"})

        try:
            while True:
                msg = await websocket.receive_json()
                if msg.get("type") != "audio" or busy:
                    continue
                busy = True
                audio_bytes = base64.b64decode(msg["data"])
                await _handle_audio(websocket, llm, memory, speaker, audio_bytes)
                busy = False
        except WebSocketDisconnect:
            logger.info("Browser disconnected")

    return app


async def _handle_audio(
    websocket: WebSocket,
    llm: ConversationManager,
    memory: MemoryStore,
    speaker,
    audio_bytes: bytes,
):
    loop = asyncio.get_running_loop()
    sentence_queue: asyncio.Queue = asyncio.Queue()

    def store_turn(user_text, robot_text, user_label, assistant_label):
        memory.store(user_text, robot_text, user_label, assistant_label)

    def stream_sentences():
        try:
            for sentence in llm.generate_response_stream(audio_bytes, store_turn):
                loop.call_soon_threadsafe(sentence_queue.put_nowait, sentence)
        except Exception as e:
            logger.error(f"Stream error: {e}")
        finally:
            loop.call_soon_threadsafe(sentence_queue.put_nowait, None)

    await websocket.send_json({"type": "state", "state": "thinking"})
    loop.run_in_executor(None, stream_sentences)

    speaking = False
    while True:
        sentence = await sentence_queue.get()
        if sentence is None:
            break
        text = sanitize_for_speech(sentence)
        if not text:
            continue
        if not speaking:
            await websocket.send_json({"type": "state", "state": "speaking"})
            speaking = True
        if speaker is not None:
            wav = await loop.run_in_executor(None, speaker.synthesize, text)
            b64 = base64.b64encode(wav).decode()
            await websocket.send_json({"type": "audio", "data": b64, "mime": "audio/wav"})
        else:
            await websocket.send_json({"type": "speak", "text": text})

    await websocket.send_json({"type": "state", "state": "idle"})
