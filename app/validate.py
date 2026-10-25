import re

PRONOUNS = {"that", "it", "this", "that one", "this one", "that task", "that todo", "the last one"}
STOPWORDS = {"the", "a", "an", "my", "task", "todo", "item", "one", "to", "please"}
ORDINALS = {"1": 0, "first": 0, "one": 0, "2": 1, "second": 1, "two": 1,
            "3": 2, "third": 2, "three": 2, "4": 3, "fourth": 3, "four": 3, "last": -1}
MAX_TEXT = 200


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", text.lower())) - STOPWORDS


def check_args(tool: dict, args: dict) -> list[str]:
    """Schema check of the model's proposed arguments. Returns error messages."""
    params = tool["parameters"]
    errors = []
    for key in params.get("required", []):
        if key not in args:
            errors.append(f"missing '{key}'")
    for key, value in args.items():
        spec = params["properties"].get(key)
        if spec is None:
            errors.append(f"unexpected '{key}'")
        elif not isinstance(value, str) or not value.strip():
            errors.append(f"'{key}' must be non-empty text")
        elif "enum" in spec and value not in spec["enum"]:
            errors.append(f"'{key}' must be one of {spec['enum']}")
        elif len(value) > MAX_TEXT:
            errors.append(f"'{key}' is longer than {MAX_TEXT} characters")
    return errors


def match(target: str, todos: list[dict], last_id: int | None) -> list[dict]:
    """Resolve the user's words to todos. Caller handles 0 / 1 / many."""
    t = target.strip().lower()
    if t in PRONOUNS:
        return [x for x in todos if x["id"] == last_id]
    exact = [x for x in todos if x["text"].lower() == t]
    if exact:
        return exact
    words = tokens(t)
    if not words:
        return []
    return [x for x in todos if words <= tokens(x["text"])]


def resolve_choice(reply: str, candidates: list[dict]) -> dict | None:
    """Answer to a clarifying question: "2", "the second one", or words that narrow to one."""
    r = reply.strip().lower().rstrip(".!?")
    m = re.fullmatch(r"(?:the\s+)?(?:number\s+)?(\w+)(?:\s+one)?", r)
    if m and m.group(1) in ORDINALS:
        i = ORDINALS[m.group(1)]
        return candidates[i] if i < len(candidates) else None
    exact = [c for c in candidates if c["text"].lower() == r]
    if len(exact) == 1:
        return exact[0]
    words = tokens(r)
    narrowed = [c for c in candidates if words and words <= tokens(c["text"])]
    return narrowed[0] if len(narrowed) == 1 else None
