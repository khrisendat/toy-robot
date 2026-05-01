import asyncio
import base64
import logging
import time
from typing import AsyncIterator

from ..hardware.wake_word import WakeWordStreamHandler
from ..lib.command_recorder import CommandRecorder
from ..lib.memory_manager import MemoryManager
from ..lib.speech import sanitize_for_speech

logger = logging.getLogger(__name__)

# States: wake | listening | push_to_talk | follow_up | busy
_WAKE = "wake"
_LISTENING = "listening"
_PUSH_TO_TALK = "push_to_talk"
_FOLLOW_UP = "follow_up"
_BUSY = "busy"


class RobotSession:
    def __init__(self, llm, memory: MemoryManager, speaker=None, speaker_id=None):
        self._llm = llm
        self._memory = memory
        self._speaker = speaker
        self._speaker_id = speaker_id  # SpeakerIdentifier | None
        self._wake = WakeWordStreamHandler()
        self._recorder = CommandRecorder()
        self._state = _WAKE
        self._follow_up_deadline: float | None = None

    async def handle(self, msg: dict) -> AsyncIterator[dict]:
        msg_type = msg.get("type")

        if self._state == _BUSY:
            return

        if msg_type == "push_to_talk":
            async for reply in self._on_push_to_talk():
                yield reply
            return

        if msg_type == "push_to_talk_end":
            async for reply in self._on_push_to_talk_end():
                yield reply
            return

        if msg_type != "audio_chunk":
            return

        pcm = base64.b64decode(msg["data"])
        async for reply in self._on_audio_chunk(pcm):
            yield reply

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def _on_push_to_talk(self) -> AsyncIterator[dict]:
        if self._state in (_WAKE, _FOLLOW_UP):
            self._wake.reset()
            self._recorder = CommandRecorder()
            self._state = _PUSH_TO_TALK
            self._follow_up_deadline = None
            yield {"type": "state", "state": "listening"}

    async def _on_push_to_talk_end(self) -> AsyncIterator[dict]:
        if self._state != _PUSH_TO_TALK:
            return
        wav = self._recorder.finalize()
        if wav is not None:
            self._state = _BUSY
            async for reply in self._stream_response(wav):
                yield reply
            async for reply in self._after_response():
                yield reply
        else:
            self._state = _WAKE
            yield {"type": "state", "state": "sleeping"}

    async def _on_audio_chunk(self, pcm: bytes) -> AsyncIterator[dict]:
        if self._state == _FOLLOW_UP and self._follow_up_deadline is not None:
            if time.monotonic() > self._follow_up_deadline:
                self._state = _WAKE

        if self._state == _WAKE:
            if self._wake.process_chunk(pcm):
                self._wake.reset()
                self._recorder = CommandRecorder()
                self._state = _LISTENING
                yield {"type": "state", "state": "listening"}

        elif self._state in (_LISTENING, _FOLLOW_UP):
            wav = self._recorder.feed(pcm)
            if wav is not None:
                self._state = _BUSY
                async for reply in self._stream_response(wav):
                    yield reply
                async for reply in self._after_response():
                    yield reply

    # ------------------------------------------------------------------
    # Response streaming
    # ------------------------------------------------------------------

    async def _stream_response(self, wav: bytes) -> AsyncIterator[dict]:
        loop = asyncio.get_running_loop()
        sentence_queue: asyncio.Queue = asyncio.Queue()

        def store_turn(user_text, robot_text, user_label, assistant_label):
            self._memory.store(user_text, robot_text, user_label, assistant_label)

        speaker_name = (
            self._speaker_id.identify(wav) if self._speaker_id else None
        )

        def stream_sentences():
            try:
                for sentence in self._llm.generate_response_stream(wav, store_turn, speaker_name=speaker_name):
                    loop.call_soon_threadsafe(sentence_queue.put_nowait, sentence)
            except Exception as e:
                logger.error(f"Stream error: {e}")
            finally:
                loop.call_soon_threadsafe(sentence_queue.put_nowait, None)

        yield {"type": "state", "state": "thinking"}
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
                yield {"type": "state", "state": "speaking"}
                speaking = True
            if self._speaker is not None:
                wav_out = await loop.run_in_executor(None, self._speaker.synthesize, text)
                b64 = base64.b64encode(wav_out).decode()
                yield {"type": "audio", "data": b64, "mime": "audio/wav"}
            else:
                yield {"type": "speak", "text": text}

        yield {"type": "state", "state": "sleeping"}

    async def _after_response(self) -> AsyncIterator[dict]:
        self._wake.reset()
        self._recorder = CommandRecorder()
        if self._llm._sleep_requested:
            self._llm._sleep_requested = False
            self._state = _WAKE
        else:
            self._state = _FOLLOW_UP
            self._follow_up_deadline = time.monotonic() + self._llm._cfg.follow_up_seconds
            yield {"type": "state", "state": "follow_up"}
