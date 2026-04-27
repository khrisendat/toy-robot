import asyncio
import base64
import logging
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .hardware.wake_word import WakeWordStreamHandler
from .lib.command_recorder import CommandRecorder
from .lib.memory_manager import MemoryManager
from .lib.speech import sanitize_for_speech
from .services import (
    tools as _tools,  # noqa: F401 — registers static tools into configs
)
from .services.conversation import CHILD_ROBOT_CONFIG, ConversationManager
from .services.tools import make_camera_tool

logger = logging.getLogger(__name__)


def create_app(camera=None, speaker=None) -> FastAPI:
    app = FastAPI()

    memory = MemoryManager()

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

        wake = WakeWordStreamHandler()
        recorder = CommandRecorder()
        state = "wake"  # wake | command | follow_up | busy
        follow_up_deadline: float | None = None
        push_to_talk_active = False

        await websocket.send_json({"type": "state", "state": "idle"})

        try:
            while True:
                msg = await websocket.receive_json()
                msg_type = msg.get("type")

                if state == "busy":
                    continue

                if msg_type == "push_to_talk":
                    if state in ("wake", "follow_up"):
                        wake.reset()
                        recorder = CommandRecorder()
                        state = "command"
                        push_to_talk_active = True
                        follow_up_deadline = None
                        await websocket.send_json({"type": "state", "state": "listening"})
                    continue

                if msg_type == "push_to_talk_end":
                    if state == "command" and push_to_talk_active:
                        push_to_talk_active = False
                        wav = recorder.finalize()
                        if wav is not None:
                            state = "busy"
                            await _handle_audio(websocket, llm, memory, speaker, wav)
                            wake.reset()
                            recorder = CommandRecorder()
                            state = "follow_up"
                            follow_up_deadline = time.monotonic() + 90
                            await websocket.send_json({"type": "state", "state": "follow_up"})
                        else:
                            state = "wake"
                            await websocket.send_json({"type": "state", "state": "idle"})
                    continue

                if msg_type != "audio_chunk":
                    continue

                pcm = base64.b64decode(msg["data"])

                if (
                    state == "follow_up"
                    and follow_up_deadline is not None
                    and time.monotonic() > follow_up_deadline
                ):
                    state = "wake"

                if state == "wake":
                    if wake.process_chunk(pcm):
                        wake.reset()
                        recorder = CommandRecorder()
                        state = "command"
                        push_to_talk_active = False
                        await websocket.send_json({"type": "state", "state": "listening"})

                elif state in ("command", "follow_up"):
                    wav = recorder.feed(pcm)
                    if wav is not None:
                        state = "busy"
                        push_to_talk_active = False
                        await _handle_audio(websocket, llm, memory, speaker, wav)
                        wake.reset()
                        recorder = CommandRecorder()
                        state = "follow_up"
                        follow_up_deadline = time.monotonic() + 90
                        await websocket.send_json({"type": "state", "state": "follow_up"})

        except WebSocketDisconnect:
            logger.info("Browser disconnected")

    return app


async def _handle_audio(
    websocket: WebSocket,
    llm: ConversationManager,
    memory: MemoryManager,
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
