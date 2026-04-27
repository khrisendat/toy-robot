import asyncio
import time

import pytest

from src.lib.robot_session import (
    _BUSY,
    _FOLLOW_UP,
    _LISTENING,
    _PUSH_TO_TALK,
    _WAKE,
    RobotSession,
)


def run(agen):
    """Collect all items from an async generator synchronously."""
    async def _collect():
        return [item async for item in agen]
    return asyncio.run(_collect())


def states_from(replies):
    return [r["state"] for r in replies if r.get("type") == "state"]


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

class _Wake:
    def __init__(self, detects=False):
        self._detects = detects
        self.reset_count = 0

    def process_chunk(self, pcm):
        return self._detects

    def reset(self):
        self.reset_count += 1


class _Recorder:
    def __init__(self, feed_result=None, finalize_result=None):
        self._feed_result = feed_result
        self._finalize_result = finalize_result

    def feed(self, pcm):
        return self._feed_result

    def finalize(self):
        return self._finalize_result


class _LLM:
    def __init__(self, sentences=("Hello.",), sleep_requested=False):
        self._sentences = sentences
        self._sleep_requested = sleep_requested
        self._cfg = type("cfg", (), {"follow_up_seconds": 10})()

    def generate_response_stream(self, wav, store_memory=None):
        yield from self._sentences


class _Memory:
    profile = {}

    def store(self, *a):
        pass

    def build_context(self, q):
        return ""


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def session():
    s = RobotSession.__new__(RobotSession)
    s._llm = _LLM()
    s._memory = _Memory()
    s._speaker = None
    s._state = _WAKE
    s._follow_up_deadline = None
    s._wake = _Wake()
    s._recorder = _Recorder()
    return s


# ---------------------------------------------------------------------------
# State-machine transitions (no response generation)
# ---------------------------------------------------------------------------

class TestPushToTalk:
    def test_from_wake_transitions_to_push_to_talk(self, session):
        run(session.handle({"type": "push_to_talk"}))
        assert session._state == _PUSH_TO_TALK

    def test_from_wake_yields_listening(self, session):
        replies = run(session.handle({"type": "push_to_talk"}))
        assert states_from(replies) == ["listening"]

    def test_from_follow_up_transitions(self, session):
        session._state = _FOLLOW_UP
        run(session.handle({"type": "push_to_talk"}))
        assert session._state == _PUSH_TO_TALK

    def test_from_listening_is_ignored(self, session):
        session._state = _LISTENING
        replies = run(session.handle({"type": "push_to_talk"}))
        assert replies == []
        assert session._state == _LISTENING

    def test_clears_follow_up_deadline(self, session):
        session._state = _FOLLOW_UP
        session._follow_up_deadline = time.monotonic() + 100
        run(session.handle({"type": "push_to_talk"}))
        assert session._follow_up_deadline is None


class TestPushToTalkEnd:
    def test_ignored_when_not_in_push_to_talk_state(self, session):
        session._state = _WAKE
        replies = run(session.handle({"type": "push_to_talk_end"}))
        assert replies == []

    def test_no_audio_yields_sleeping_and_reverts_to_wake(self, session):
        session._state = _PUSH_TO_TALK
        session._recorder = _Recorder(finalize_result=None)
        replies = run(session.handle({"type": "push_to_talk_end"}))
        assert states_from(replies) == ["sleeping"]
        assert session._state == _WAKE

    def test_with_audio_enters_busy_then_follow_up(self, session):
        session._state = _PUSH_TO_TALK
        session._recorder = _Recorder(finalize_result=b"fakeWAV")
        run(session.handle({"type": "push_to_talk_end"}))
        assert session._state == _FOLLOW_UP

    def test_with_audio_yields_thinking_and_speaking(self, session):
        session._state = _PUSH_TO_TALK
        session._recorder = _Recorder(finalize_result=b"fakeWAV")
        replies = run(session.handle({"type": "push_to_talk_end"}))
        states = states_from(replies)
        assert "thinking" in states
        assert "speaking" in states


class TestAudioChunk:
    def test_unknown_message_type_yields_nothing(self, session):
        replies = run(session.handle({"type": "other"}))
        assert replies == []

    def test_busy_state_ignores_audio(self, session):
        session._state = _BUSY
        replies = run(session.handle({"type": "audio_chunk", "data": ""}))
        assert replies == []

    def test_no_wake_word_yields_nothing(self, session):
        session._wake = _Wake(detects=False)
        import base64
        pcm = base64.b64encode(b"\x00" * 320).decode()
        replies = run(session.handle({"type": "audio_chunk", "data": pcm}))
        assert replies == []
        assert session._state == _WAKE

    def test_wake_word_detected_yields_listening(self, session):
        session._wake = _Wake(detects=True)
        import base64
        pcm = base64.b64encode(b"\x00" * 320).decode()
        replies = run(session.handle({"type": "audio_chunk", "data": pcm}))
        assert states_from(replies) == ["listening"]
        assert session._state == _LISTENING

    def test_follow_up_timeout_reverts_to_wake_before_processing(self, session):
        session._state = _FOLLOW_UP
        session._follow_up_deadline = time.monotonic() - 1  # already expired
        session._wake = _Wake(detects=False)
        import base64
        pcm = base64.b64encode(b"\x00" * 320).decode()
        run(session.handle({"type": "audio_chunk", "data": pcm}))
        assert session._state == _WAKE

    def test_vad_trigger_in_listening_starts_response(self, session):
        session._state = _LISTENING
        session._recorder = _Recorder(feed_result=b"fakeWAV")
        import base64
        pcm = base64.b64encode(b"\x00" * 320).decode()
        replies = run(session.handle({"type": "audio_chunk", "data": pcm}))
        states = states_from(replies)
        assert "thinking" in states


# ---------------------------------------------------------------------------
# Post-response state transitions
# ---------------------------------------------------------------------------

class TestAfterResponse:
    def _run_response(self, session):
        session._state = _PUSH_TO_TALK
        session._recorder = _Recorder(finalize_result=b"fakeWAV")
        return run(session.handle({"type": "push_to_talk_end"}))

    def test_no_sleep_goes_to_follow_up(self, session):
        session._llm = _LLM(sleep_requested=False)
        self._run_response(session)
        assert session._state == _FOLLOW_UP

    def test_no_sleep_sets_follow_up_deadline(self, session):
        session._llm = _LLM(sleep_requested=False)
        before = time.monotonic()
        self._run_response(session)
        assert session._follow_up_deadline is not None
        assert session._follow_up_deadline > before

    def test_sleep_requested_goes_to_wake(self, session):
        session._llm = _LLM(sleep_requested=True)
        self._run_response(session)
        assert session._state == _WAKE

    def test_sleep_requested_cleared_after_response(self, session):
        session._llm = _LLM(sleep_requested=True)
        self._run_response(session)
        assert session._llm._sleep_requested is False
