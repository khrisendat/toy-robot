import asyncio
import base64
import logging
import re

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .services.conversation import ConversationManager, CHILD_ROBOT_CONFIG
from .lib.memory import MemoryStore
from .services import tools as _tools  # noqa: F401 — registers static tools into configs
from .services.tools import make_camera_tool

logger = logging.getLogger(__name__)

_EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0\U000024C2-\U0001F251]+",
    flags=re.UNICODE,
)


def _sanitize(text: str) -> str:
    text = _EMOJI_RE.sub("", text)
    text = re.sub(r"tool_code\s*\n[\s\S]*", "", text)
    text = re.sub(r"[*#_~`|<>^]", "", text)
    return re.sub(r" +", " ", text).strip()


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
        await websocket.send_json({"type": "state", "state": "idle"})

        try:
            while True:
                msg = await websocket.receive_json()
                if msg.get("type") == "audio":
                    await _handle_audio(websocket, llm, memory, speaker, msg["data"])
        except WebSocketDisconnect:
            logger.info("Browser disconnected")

    return app


async def _handle_audio(
    websocket: WebSocket,
    llm: ConversationManager,
    memory: MemoryStore,
    speaker,
    audio_b64: str,
):
    audio_bytes = base64.b64decode(audio_b64)
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

    loop = asyncio.get_running_loop()
    speaking = False
    while True:
        sentence = await sentence_queue.get()
        if sentence is None:
            break
        text = _sanitize(sentence)
        if not text:
            continue
        if not speaking:
            await websocket.send_json({"type": "state", "state": "speaking"})
            speaking = True
        if speaker is not None:
            audio_bytes = await loop.run_in_executor(None, speaker.synthesize, text)
            if audio_bytes:
                b64 = base64.b64encode(audio_bytes).decode()
                await websocket.send_json({"type": "audio", "data": b64, "mime": "audio/wav"})
                continue
        # fallback to browser TTS if no speaker
        await websocket.send_json({"type": "speak", "text": text})

    await websocket.send_json({"type": "state", "state": "idle"})
