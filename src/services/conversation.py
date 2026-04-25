import logging
import re
import time
from dataclasses import dataclass, field
from typing import Callable, Optional
from .. import config
from ..lib.gemini import GeminiClient


def _extract_sentences(text):
    """Return (complete_sentences, incomplete_remainder) by splitting on sentence-ending punctuation."""
    parts = re.split(r'(?<=[.!?])\s+', text)
    if len(parts) <= 1:
        return [], text
    return parts[:-1], parts[-1]


logger = logging.getLogger(__name__)


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON Schema (OpenAPI 3.0 subset)
    handler: Callable  # called with kwargs matching parameter names; must return dict or str

    @property
    def declaration(self) -> dict:
        return {"name": self.name, "description": self.description, "parameters": self.parameters}


@dataclass
class ConversationConfig:
    system_prompt: str
    audio_instruction: str = "Respond to the user."
    vision_signal: Optional[str] = None
    vision_instruction: str = "Describe what you see in this image."
    user_label: str = "User"
    assistant_label: str = "Assistant"
    tools: list = field(default_factory=list)  # list[Tool]


CHILD_ROBOT_CONFIG = ConversationConfig(
    system_prompt=(
        f"You are a friendly robot assistant for a four-year-old named {config.USER_NAME}. "
        "Be kind, simple, and creative. Your response should be brief — just one or two sentences. "
        "Do not use emojis, asterisks, bullet points, or any special characters — only plain spoken words. "
        "Vary your tone and energy to keep things fun and surprising. "
        "About half the time, end your response with a simple, playful follow-up question to keep the conversation going. "
        "If the user asks you to look at something or describe what you see, respond with exactly 'NEED_CAMERA' and nothing else. "
        "You have a web_search tool available. You MUST call it for any question about current events, news, weather, movies, sports scores, or anything that changes over time — do not guess or say you don't know, search first."
    ),
    audio_instruction="Respond to what the child said.",
    vision_signal="NEED_CAMERA",
    vision_instruction="Describe what you see in this image to the child in one or two fun sentences.",
    user_label="Child",
    assistant_label="Robot",
)

PERSONAL_ASSISTANT_CONFIG = ConversationConfig(
    system_prompt=(
        "You are a helpful personal assistant. Be concise and direct. "
        "Use plain text only — no emojis, asterisks, or special formatting. "
        "You have access to tools — use them whenever they would give a more accurate answer."
    ),
    user_label="User",
    assistant_label="Assistant",
    # tools are added at import time from tools.py to avoid a circular import;
    # see the bottom of tools.py, or set them explicitly:
    #   PERSONAL_ASSISTANT_CONFIG.tools = [get_current_datetime, calculate]
)


class ConversationManager:
    def __init__(self, cfg: ConversationConfig = CHILD_ROBOT_CONFIG, memory=None):
        self._client = GeminiClient()
        self._cfg = cfg
        self._history = []  # list of {"role": ..., "parts": [...]} dicts (text only)
        self.memory = memory

    def generate_response(self, audio_data, get_image=None, store_memory=None):
        """
        Generate a response for the given input.

        audio_data:   bytes (WAV) for real mic input, or str for mock/text input
        get_image:    optional callable() → bytes — invoked when the model requests vision
        store_memory: optional callable(user_text, robot_text, user_label, assistant_label)
        """
        logger.info(f"Sending to LLM ({self._client.model})...")

        user_parts, history_text = self._prepare_input(audio_data)
        system_prompt = self._build_system_prompt(history_text)
        start = time.time()

        try:
            text, tool_turns = self._call(user_parts, system_prompt)

            if self._cfg.vision_signal and text.strip() == self._cfg.vision_signal and get_image is not None:
                logger.info("Vision requested — capturing image.")
                image_data = get_image()
                if image_data:
                    vision_parts = [
                        self._client.encode_image(image_data),
                        {"text": self._cfg.vision_instruction},
                    ]
                    text = self._call(vision_parts, system_prompt)
                    history_text = "[asked to look]"
                else:
                    text = "I tried to look but my camera isn't working right now!"
                    history_text = "[camera failed]"

            if self._cfg.vision_signal and text.strip() == self._cfg.vision_signal:
                text = "I tried to look but I couldn't quite see. Can you describe it to me?"

            self._history.append({"role": "user", "parts": [{"text": history_text}]})
            self._history.extend(tool_turns)
            self._history.append({"role": "model", "parts": [{"text": text}]})
            logger.info(f"LLM response ({time.time() - start:.2f}s): {text}")

            if store_memory is not None:
                store_memory(history_text, text, self._cfg.user_label, self._cfg.assistant_label)

            return text

        except Exception as e:
            elapsed = time.time() - start
            import requests as req
            if isinstance(e, req.Timeout):
                logger.warning(f"LLM timed out after {elapsed:.2f}s")
                return "I'm sorry, I'm taking too long to think. Can you try again?"
            logger.error(f"LLM error after {elapsed:.2f}s: {e}")
            return "I'm sorry, I'm having a little trouble thinking right now."

    def generate_response_stream(self, audio_data, get_image=None, store_memory=None):
        """Yield sentences as they are generated."""
        user_parts, history_text = self._prepare_input(audio_data)
        system_prompt = self._build_system_prompt(history_text)
        contents = self._history + [{"role": "user", "parts": user_parts}]
        start = time.time()
        full_text = ""
        tool_turns = []

        try:
            if self._cfg.tools:
                # Tool calls require multi-turn round-trips; collect full response then yield
                full_text, tool_turns = self._run_tool_loop(contents, system_prompt)
                sentences, leftover = _extract_sentences(full_text + " ")
                for s in sentences:
                    yield s
                if leftover.strip():
                    yield leftover.strip()
            else:
                buffer = ""
                for chunk in self._client.generate_stream(contents, system_prompt):
                    full_text += chunk
                    buffer += chunk
                    sentences, buffer = _extract_sentences(buffer)
                    for sentence in sentences:
                        yield sentence

                remaining = buffer.strip()
                if self._cfg.vision_signal and remaining == self._cfg.vision_signal:
                    logger.info("Vision requested — capturing image.")
                    if get_image is not None:
                        image_data = get_image()
                        if image_data:
                            vision_parts = [
                                self._client.encode_image(image_data),
                                {"text": self._cfg.vision_instruction},
                            ]
                            full_text = self._client.generate(contents + [{"role": "user", "parts": vision_parts}], system_prompt)
                            history_text = "[asked to look]"
                        else:
                            full_text = "I tried to look but my camera isn't working right now!"
                            history_text = "[camera failed]"
                    else:
                        full_text = "I tried to look but I couldn't quite see. Can you describe it to me?"
                    sentences, leftover = _extract_sentences(full_text + " ")
                    for sentence in sentences:
                        yield sentence
                    if leftover.strip():
                        yield leftover.strip()
                elif remaining:
                    yield remaining

        except Exception as e:
            elapsed = time.time() - start
            import requests as req
            if isinstance(e, req.Timeout):
                logger.warning(f"LLM timed out after {elapsed:.2f}s")
                yield "I'm sorry, I'm taking too long to think. Can you try again?"
                return
            logger.error(f"LLM error after {elapsed:.2f}s: {e}")
            yield "I'm sorry, I'm having a little trouble thinking right now."
            return

        logger.info(f"LLM complete ({time.time() - start:.2f}s): {full_text}")
        self._history.append({"role": "user", "parts": [{"text": history_text}]})
        self._history.extend(tool_turns)
        self._history.append({"role": "model", "parts": [{"text": full_text}]})
        if store_memory is not None:
            store_memory(history_text, full_text, self._cfg.user_label, self._cfg.assistant_label)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _prepare_input(self, audio_data):
        if isinstance(audio_data, bytes):
            user_parts = [
                self._client.encode_audio(audio_data),
                {"text": self._cfg.audio_instruction},
            ]
            history_text = "[voice input]"
        else:
            user_parts = [{"text": audio_data}]
            history_text = audio_data
        return user_parts, history_text

    def _call(self, user_parts: list, system_prompt: str):
        """Returns (text, tool_turns) where tool_turns is the list of intermediate
        functionCall/functionResponse history entries produced during tool use."""
        contents = self._history + [{"role": "user", "parts": user_parts}]
        if not self._cfg.tools:
            return self._client.generate(contents, system_prompt), []
        return self._run_tool_loop(contents, system_prompt)

    def _run_tool_loop(self, contents: list, system_prompt: str):
        """Execute the tool-call loop. Returns (final_text, tool_turns)."""
        declarations = [t.declaration for t in self._cfg.tools]
        tool_map = {t.name: t.handler for t in self._cfg.tools}
        tool_turns = []

        for _ in range(5):
            result = self._client.generate_turn(contents, system_prompt, declarations)

            if "text" in result:
                return result["text"], tool_turns

            call = result["function_call"]
            name, args, call_id = call["name"], call["args"], call.get("id")
            logger.info(f"Tool call: {name}({args})")

            handler = tool_map.get(name)
            try:
                tool_result = handler(**args) if handler else {"error": f"Unknown tool: {name}"}
                if not isinstance(tool_result, dict):
                    tool_result = {"result": str(tool_result)}
            except Exception as e:
                tool_result = {"error": str(e)}
            logger.info(f"Tool result: {tool_result}")

            fc_part = {"functionCall": {"name": name, "args": args}}
            fr_part = {"functionResponse": {"name": name, "response": tool_result}}
            if call_id:
                fc_part["functionCall"]["id"] = call_id
                fr_part["functionResponse"]["id"] = call_id

            model_turn = {"role": "model", "parts": [fc_part]}
            user_turn = {"role": "user", "parts": [fr_part]}
            tool_turns.extend([model_turn, user_turn])
            contents = contents + [model_turn, user_turn]

        return "I had trouble completing that request.", tool_turns

    def _build_system_prompt(self, query: str) -> str:
        if self.memory is None:
            return self._cfg.system_prompt
        memories = self.memory.search(query, top_k=3)
        if not memories:
            return self._cfg.system_prompt
        memory_block = "\n".join(f"- {m}" for m in memories)
        logger.debug(f"[Memory] Injecting {len(memories)} memories into prompt")
        return (
            self._cfg.system_prompt
            + "\n\nRelevant memories from past conversations:\n"
            + memory_block
        )
