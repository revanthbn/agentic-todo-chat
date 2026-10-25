import json
import os
import re

import yaml

from app.validate import PRONOUNS, lexical

DEFAULT_MODEL = "anthropic/claude-haiku-5-5"


class MockLLM:
    """Keyword/regex stand-in for the model. Same inputs/outputs as LiteLLMClient.

    Deliberately small: anything it can't parse is listed in PROCESS.md.
    """

    mode = "mock"

    ROUTES = [  # order matters: first match wins
        ("update", r"\b(change|rename|update|edit|modify|reword)\b|\bmake (that|it|this)\b"),
        ("complete", r"\b(complete|finish|finished|done|mark|check off|tick off)\b"),
        ("delete", r"\b(delete|remove|drop|cancel)\b"),
        ("add", r"\b(add|create|new|remind me to)\b"),
        ("list", r"\b(list|show|what|todos|tasks)\b"),
    ]

    def route(self, catalog: list[dict], message: str, history: list[dict]) -> str | None:
        msg = message.lower()
        if re.match(r"\s*(hi|hello|hey|help|yo|good (morning|afternoon|evening))\b", msg) or re.search(
                r"what can you do|how does this work|who are you|what do you do", msg):
            return "help"
        if re.match(r"\s*(what|which|show|list)\b", msg):  # questions: "what's done?" is a list, not complete
            return "list"
        return next((name for name, pat in self.ROUTES if re.search(pat, msg)), None)

    def act(self, skill: dict, message: str, history: list[dict], todos: list[dict]) -> dict:
        args = self._parse(skill["name"], message.strip().rstrip(".!?"))
        if "target" in args:  # stand-in for the model's semantic guess: lexical matches only
            target = args["target"].strip().lower()
            args["candidate_ids"] = [] if target in PRONOUNS else lexical(target, todos)
        return args

    def _parse(self, name: str, msg: str) -> dict:
        if name == "add":
            text = re.sub(
                r"^(please\s+)?((add|create)(\s+a)?(\s+new)?(\s+(task|todo))?(\s+(to|called|named))?:?|remind me to)\s+",
                "", msg, flags=re.I)
            return {"text": text}
        if name == "list":
            low = msg.lower()
            if re.search(r"\b(done|completed|finished)\b", low):
                return {"status": "done"}
            if re.search(r"\b(open|remaining|left|pending)\b", low):
                return {"status": "open"}
            return {"status": "all"}
        if name == "update":
            m = re.search(r"\b(?:change|rename|update|edit|modify|reword)\s+(.+?)\s+to\s+(.+)$", msg, flags=re.I)
            if m:
                return {"target": m.group(1), "text": m.group(2)}
            m = re.search(r"\bmake\s+(that|it|this)\s+(.+)$", msg, flags=re.I)
            return {"target": m.group(1), "text": m.group(2)} if m else {}
        if name == "complete":
            target = re.sub(r"^(please\s+)?(mark|complete|finish|check off|tick off)\s+", "", msg, flags=re.I)
            target = re.sub(r"\s+(as\s+)?(done|complete|completed|finished)$", "", target, flags=re.I)
            return {"target": target}
        if name == "delete":
            return {"target": re.sub(r"^(please\s+)?(delete|remove|drop|cancel)\s+", "", msg, flags=re.I)}
        return {}


class LiteLLMClient:
    mode = "live"

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model

    def _call(self, system: str, messages: list[dict], tool: dict) -> dict:
        import litellm

        litellm.suppress_debug_info = True
        resp = litellm.completion(
            model=self.model,
            messages=[{"role": "system", "content": system}, *messages],
            tools=[{"type": "function", "function": tool}],
            tool_choice={"type": "function", "function": {"name": tool["name"]}},
            max_tokens=300,
        )
        calls = resp.choices[0].message.tool_calls or []
        return json.loads(calls[0].function.arguments) if calls else {}

    def route(self, catalog: list[dict], message: str, history: list[dict]) -> str | None:
        names = [s["name"] for s in catalog]
        system = (
            "You route a todo-list chat message to exactly one skill.\n"
            f"Skills:\n{yaml.safe_dump(catalog, sort_keys=False)}"
        )
        tool = {
            "name": "choose_skill",
            "description": "Pick the skill that handles the user's latest message.",
            "parameters": {
                "type": "object",
                "properties": {"skill": {"type": "string", "enum": names}},
                "required": ["skill"],
            },
        }
        return self._call(system, [*history[-6:], {"role": "user", "content": message}], tool).get("skill")

    def act(self, skill: dict, message: str, history: list[dict], todos: list[dict]) -> dict:
        # The one loaded skill, recent messages and the todos (so the model can propose
        # candidate_ids). The model only proposes; check() decides which todo is meant.
        listing = "\n".join(f"- id {t['id']}: {t['text']}{' (done)' if t['completed'] else ''}" for t in todos)
        system = f"{skill['instructions']}\n\nCurrent todos:\n{listing or '(none)'}"
        return self._call(system, [*history, {"role": "user", "content": message}], skill["tool"])


def get_llm():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return LiteLLMClient(os.environ.get("LLM_MODEL", DEFAULT_MODEL))
    return MockLLM()
