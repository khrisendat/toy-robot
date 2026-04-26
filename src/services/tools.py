"""
Ready-to-use tools for ConversationConfig.

Each tool is a Tool(...) instance. Add your own by following the same pattern:
  - `parameters` is a JSON Schema object (OpenAPI 3.0 subset)
  - `handler` is called with kwargs matching the parameter names
  - handler must return a dict (or a value that will be wrapped in {"result": ...})
"""

import ast
import datetime
import logging
import operator

import requests

from .. import config
from .conversation import Tool

logger = logging.getLogger(__name__)


get_current_datetime = Tool(
    name="get_current_datetime",
    description="Returns the current date and time.",
    parameters={"type": "object", "properties": {}},
    handler=lambda: {"datetime": datetime.datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")},
)


def _eval_node(node):
    safe_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        op = safe_ops.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op(_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp):
        op = safe_ops.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op(_eval_node(node.operand))
    raise ValueError(f"Unsupported expression: {type(node).__name__}")


def _calculate(expression: str) -> dict:
    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval_node(tree.body)
        return {"result": str(result)}
    except Exception as e:
        return {"error": str(e)}


calculate = Tool(
    name="calculate",
    description="Evaluates an arithmetic expression and returns the result.",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "A math expression, e.g. '(12 * 4) / 3'",
            }
        },
        "required": ["expression"],
    },
    handler=_calculate,
)


def _web_search(query: str, count: int = 3) -> dict:
    if not config.BRAVE_API_KEY:
        return {"error": "BRAVE_API_KEY is not set."}
    try:
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": config.BRAVE_API_KEY,
            },
            params={"q": query, "count": count, "safesearch": "strict"},
            timeout=10,
        )
        response.raise_for_status()
        results = response.json().get("web", {}).get("results", [])
        if not results:
            return {"results": "No results found."}
        summaries = [
            f"{r['title']}: {r.get('description', '').strip()}"
            for r in results
        ]
        logger.info(f"[Search] '{query}' → {len(summaries)} results")
        return {"results": "\n".join(summaries)}
    except Exception as e:
        logger.error(f"[Search] Error: {e}")
        return {"error": str(e)}


web_search = Tool(
    name="web_search",
    description="Search the web for up-to-date information on any topic.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query.",
            }
        },
        "required": ["query"],
    },
    handler=_web_search,
)


def make_camera_tool(get_image):
    """Factory that returns a capture_image Tool bound to the given get_image callable."""
    def _capture():
        data = get_image()
        if data is None:
            return {"error": "Camera capture failed."}
        return {"__inline_data__": {"mimeType": "image/jpeg", "data": data}}

    return Tool(
        name="capture_image",
        description="Capture an image from the camera to see what is in front of you.",
        parameters={"type": "object", "properties": {}},
        handler=_capture,
    )


# Wire static tools into presets.
from .conversation import CHILD_ROBOT_CONFIG, PERSONAL_ASSISTANT_CONFIG  # noqa: E402

CHILD_ROBOT_CONFIG.tools = [web_search]
PERSONAL_ASSISTANT_CONFIG.tools = [get_current_datetime, calculate, web_search]
