import re

_EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0\U000024C2-\U0001F251]+",
    flags=re.UNICODE,
)


def sanitize_for_speech(text: str) -> str:
    text = _EMOJI_RE.sub("", text)
    text = re.sub(r"<think(?:ing)?>\s*[\s\S]*?</think(?:ing)?>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"tool_code\s*\n[\s\S]*", "", text)
    text = re.sub(r"[*#_~`|<>^]", "", text)
    return re.sub(r" +", " ", text).strip()
