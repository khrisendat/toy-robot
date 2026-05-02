import base64
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Callable

from .. import config
from ..lib.gemini import GeminiClient
from ..lib.robot_memory import strip_annotations


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
    user_label: str = "User"
    assistant_label: str = "Assistant"
    tools: list = field(default_factory=list)  # list[Tool]
    thinking_budget: int = -1  # -1 = dynamic, 0 = disabled, 1-24576 = fixed cap
    follow_up_seconds: int = 90


_ANNOTATION_INSTRUCTION = (
    "When you learn a personal fact about the child (a name they want to be called, a family member, a pet), "
    "silently append [MEMORY profile key=\"value\"] at the very end of your response. "
    "When you learn what the child likes, dislikes, or is afraid of, "
    "append [MEMORY preference key=\"value\"] at the very end. "
    "If the child gives you a new name to call yourself, append [MEMORY profile robot_name=\"name\"]. "
    "Use short lowercase keys like: called, age, pet, sibling, likes, dislikes, scared_of, robot_name. "
    "Only annotate genuinely new information not already in your context. Never say the tags aloud. "
    "When Kabir says goodbye or goodnight, respond warmly and append [SLEEP] at the very end."
)

CHILD_ROBOT_CONFIG = ConversationConfig(
    system_prompt=(
        f"You are a friendly robot assistant for a four-year-old named {config.USER_NAME}. "
        "Be kind, simple, and creative. Your response should be brief — just one or two sentences. "
        "Do not use emojis, asterisks, bullet points, code blocks, or any special characters — only plain spoken words. "
        "Never output code. "
        "Vary your tone and energy to keep things fun and surprising. "
        "About half the time, end your response with a simple, playful follow-up question to keep the conversation going. "
        "You have a capture_image tool — you MUST call it whenever asked to look at something, describe what you see, or identify an object. Never pretend to look or guess; always call the tool first. "
        "You have a web_search tool available. You MUST call it for any question about current events, news, weather, movies, sports scores, or anything that changes over time — do not guess or say you don't know, search first. "
        f"\n\n{_ANNOTATION_INSTRUCTION}"
    ),
    audio_instruction=(
        "Respond to what the child said. "
        "IMPORTANT: If they ask you to look at, see, or identify anything, call the capture_image tool immediately — do not describe what you will do, just call it."
    ),
    user_label="Child",
    assistant_label="Robot",
    thinking_budget=512,
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
        self._sleep_requested = False

    def generate_response(self, audio_data, store_memory=None):
        """
        Generate a response for the given input.

        audio_data:   bytes (WAV) for real mic input, or str for mock/text input
        store_memory: optional callable(user_text, robot_text, user_label, assistant_label)
        """
        logger.info(f"Sending to LLM ({self._client.model})...")

        user_parts, history_text = self._prepare_input(audio_data)
        system_prompt = self._build_system_prompt(history_text)
        start = time.time()

        try:
            text, tool_turns = self._call(user_parts, system_prompt)

            if hasattr(self.memory, "process_annotations"):
                text = self.memory.process_annotations(text)

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

    def generate_response_stream(self, audio_data, store_memory=None, speaker_name=None):
        """Yield sentences as they are generated."""
        self._sleep_requested = False
        user_parts, history_text = self._prepare_input(audio_data, speaker_name=speaker_name)
        system_prompt = self._build_system_prompt(history_text)
        contents = self._history + [{"role": "user", "parts": user_parts}]
        start = time.time()
        full_text = ""
        tool_turns = []

        declarations = [t.declaration for t in self._cfg.tools] if self._cfg.tools else None
        tool_map = {t.name: t.handler for t in self._cfg.tools} if self._cfg.tools else {}
        current_contents = contents

        try:
            for turn in range(6):  # up to 5 tool calls then a final text response
                buffer = ""
                function_call = None
                # Disable thinking after tool calls — post-tool responses are short
                # spoken sentences and Gemini 2.5 leaks thinking as plain text in that path.
                budget = self._cfg.thinking_budget if turn == 0 else 0

                for chunk in self._client.generate_stream(current_contents, system_prompt, declarations, thinking_budget=budget):
                    if isinstance(chunk, dict):
                        function_call = chunk["function_call"]
                        break
                    full_text += chunk
                    buffer += chunk
                    sentences, buffer = _extract_sentences(buffer)
                    for sentence in sentences:
                        clean = strip_annotations(sentence)
                        if clean:
                            yield clean

                if function_call is None:
                    if buffer.strip():
                        clean = strip_annotations(buffer.strip())
                        if clean:
                            yield clean
                    break

                model_turn, user_turn = self._execute_tool_call(function_call, tool_map)
                tool_turns.extend([model_turn, user_turn])
                current_contents = current_contents + [model_turn, user_turn]

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

        logger.info(f"[Response raw] {full_text}")
        self._sleep_requested = bool(re.search(r'\[SLEEP\]', full_text, re.IGNORECASE))
        if hasattr(self.memory, "process_annotations"):
            clean_full_text = self.memory.process_annotations(full_text)
        else:
            clean_full_text = re.sub(r'\[SLEEP\]', '', full_text, flags=re.IGNORECASE).strip()

        logger.info(f"[Response clean] ({time.time() - start:.2f}s): {clean_full_text}")
        self._history.append({"role": "user", "parts": [{"text": history_text}]})
        self._history.extend(tool_turns)
        self._history.append({"role": "model", "parts": [{"text": clean_full_text}]})
        if store_memory is not None:
            store_memory(history_text, clean_full_text, self._cfg.user_label, self._cfg.assistant_label)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _prepare_input(self, audio_data, speaker_name=None):
        if isinstance(audio_data, bytes):
            instruction = self._cfg.audio_instruction
            if speaker_name:
                instruction = f"You are speaking with {speaker_name}. " + instruction
            user_parts = [
                self._client.encode_audio(audio_data),
                {"text": instruction},
            ]
            history_text = "[voice input]"
        else:
            user_parts = [{"text": audio_data}]
            history_text = audio_data
        return user_parts, history_text

    def _call(self, user_parts: list, system_prompt: str):
        """Returns (text, tool_turns)."""
        contents = self._history + [{"role": "user", "parts": user_parts}]
        if not self._cfg.tools:
            return self._client.generate(contents, system_prompt), []
        return self._run_tool_loop(contents, system_prompt)

    def _execute_tool_call(self, function_call: dict, tool_map: dict):
        """Execute a tool call. Returns (model_turn, user_turn) for history.

        If the handler returns {"__inline_data__": {"mimeType": ..., "data": bytes}},
        the image is included as an inlineData part alongside the functionResponse so
        the model can process it visually.
        """
        name, args, call_id = function_call["name"], function_call["args"], function_call.get("id")
        logger.info(f"Tool call: {name}({args})")

        handler = tool_map.get(name)
        try:
            tool_result = handler(**args) if handler else {"error": f"Unknown tool: {name}"}
            if not isinstance(tool_result, dict):
                tool_result = {"result": str(tool_result)}
        except Exception as e:
            tool_result = {"error": str(e)}

        inline_data = tool_result.pop("__inline_data__", None)
        logger.info(f"Tool result: {tool_result}")

        fc_part = {"functionCall": {"name": name, "args": args}}
        response_body = tool_result if tool_result else {"status": "done"}
        if inline_data:
            response_body = {"output": "Image captured. Look at the image provided and describe what you see in plain spoken words."}
        fr_part = {"functionResponse": {"name": name, "response": response_body}}
        if call_id:
            fc_part["functionCall"]["id"] = call_id
            fr_part["functionResponse"]["id"] = call_id

        user_parts = [fr_part]
        if inline_data:
            data = inline_data["data"]
            if isinstance(data, bytes):
                data = base64.b64encode(data).decode()
            user_parts.append({"inlineData": {"mimeType": inline_data["mimeType"], "data": data}})

        return {"role": "model", "parts": [fc_part]}, {"role": "user", "parts": user_parts}

    def _run_tool_loop(self, contents: list, system_prompt: str):
        """Execute the tool-call loop (non-streaming). Returns (final_text, tool_turns)."""
        declarations = [t.declaration for t in self._cfg.tools]
        tool_map = {t.name: t.handler for t in self._cfg.tools}
        tool_turns = []

        for _ in range(5):
            result = self._client.generate_turn(contents, system_prompt, declarations, thinking_budget=self._cfg.thinking_budget)

            if "text" in result:
                return result["text"], tool_turns

            model_turn, user_turn = self._execute_tool_call(result["function_call"], tool_map)
            tool_turns.extend([model_turn, user_turn])
            contents = contents + [model_turn, user_turn]

        return "I had trouble completing that request.", tool_turns

    def _build_system_prompt(self, query: str) -> str:
        base = self._cfg.system_prompt
        if self.memory is None:
            return base

        robot_name = None
        if hasattr(self.memory, "get_robot_name"):
            robot_name = self.memory.get_robot_name()
        if robot_name:
            base = f"Your name is {robot_name}. " + base

        if hasattr(self.memory, "build_context"):
            context = self.memory.build_context(query)
        else:
            memories = self.memory.search(query, top_k=3)
            context = (
                "Relevant memories from past conversations:\n"
                + "\n".join(f"- {m}" for m in memories)
                if memories
                else ""
            )

        if not context:
            logger.info(f"[Prompt]\n{base}")
            return base
        result = base + "\n\n" + context
        logger.info(f"[Prompt]\n{result}")
        return result
