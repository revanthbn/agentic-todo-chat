import re

PRONOUNS = {"that", "it", "this", "that one", "this one", "that task", "that todo", "the last one"}
REFERENCE_WORDS = {"that", "it", "this"}  # references, never content words
STOPWORDS = {"the", "a", "an", "my", "task", "todo", "item", "one", "to", "please"} | REFERENCE_WORDS
ORDINALS = {"1": 0, "first": 0, "one": 0, "2": 1, "second": 1, "two": 1,
            "3": 2, "third": 2, "three": 2, "4": 3, "fourth": 3, "four": 3, "last": -1}
MAX_TEXT = 200


def stem(word: str) -> str:
    """Light stemmer: buying → buy, eggs → egg, called → call. Keeps 3+ letters."""
    for suffix in ("ing", "ed", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def tokens(text: str) -> set[str]:
    return {stem(w) for w in re.findall(r"[a-z0-9']+", text.lower()) if w not in STOPWORDS}


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
        elif spec.get("type") == "array":
            if not isinstance(value, list) or not all(type(v) is int for v in value):
                errors.append(f"'{key}' must be a list of integers")
        elif not isinstance(value, str) or not value.strip():
            errors.append(f"'{key}' must be non-empty text")
        elif "enum" in spec and value not in spec["enum"]:
            errors.append(f"'{key}' must be one of {spec['enum']}")
        elif len(value) > MAX_TEXT:
            errors.append(f"'{key}' is longer than {MAX_TEXT} characters")
    return errors


ADD_FILLER = {"add", "create", "new", "a", "an", "the", "task", "todo", "item", "please",
              "remind", "me", "to", "another", "one"}
PLACEHOLDER = re.compile(r"\s*(<.*>|\[.*\]|unknown|none|null|n/?a|tbd|todo|task|something|\?+)\s*", re.I)


def nothing_to_add(message: str, text: str) -> bool:
    """The user gave no task ("add") or the model filled in a placeholder ("<UNKNOWN>")."""
    words = set(re.findall(r"[a-z0-9']+", message.lower())) - ADD_FILLER
    return not words or bool(PLACEHOLDER.fullmatch(text))


def normalize(text: str) -> str:
    return " ".join(text.lower().split()).rstrip(".!?")


def find_duplicate(text: str, todos: list[dict], exclude_id: int | None = None) -> dict | None:
    """An open todo with the same text (case/spacing/trailing punctuation ignored)."""
    t = normalize(text)
    return next((x for x in todos if not x["completed"] and x["id"] != exclude_id
                 and normalize(x["text"]) == t), None)


def lexical(target: str, todos: list[dict]) -> list[int]:
    """Ids whose text contains every (stemmed) word of the target. Exact text wins."""
    exact = [x["id"] for x in todos if normalize(x["text"]) == normalize(target)]
    if exact:
        return exact
    words = tokens(target)
    return [x["id"] for x in todos if words and words <= tokens(x["text"])] if words else []


def resolve_target(target: str, model_ids: list[int], todos: list[dict],
                   last_id: int | None) -> tuple[str, list[int], list[int]]:
    """Code decides which todos the target means. Returns (how, ids, lexical_ids).

    - "that"/"it" alone → last_referenced_id (model ids ignored)
    - exact text → that todo
    - "that call" → last_referenced_id if "call" fits it, else match "call" normally
    - otherwise the union of the model's candidates and lexical matches, so the
      model can widen the set (semantic matches) but never narrow it.
    """
    ids_in_store = {x["id"] for x in todos}
    t = target.strip().lower()
    if t in PRONOUNS:
        return "pronoun", [last_id] if last_id in ids_in_store else [], []
    exact = [x["id"] for x in todos if normalize(x["text"]) == normalize(t)]
    if exact:
        return "exact", exact, exact
    if REFERENCE_WORDS & set(re.findall(r"[a-z']+", t)) and last_id in ids_in_store:
        ref = next(x for x in todos if x["id"] == last_id)
        if tokens(t) and tokens(t) <= tokens(ref["text"]):
            return "pronoun", [last_id], []
    lex = lexical(t, todos)
    return "union", sorted({i for i in model_ids if i in ids_in_store} | set(lex)), lex


def is_yes(reply: str) -> bool:
    return bool(re.match(r"\s*(y|yes|yeah|yep|sure|ok|okay|confirm|do it|go ahead)\b", reply.lower()))


def is_no(reply: str) -> bool:
    return bool(re.match(r"\s*(n|no|nope|cancel|stop|never ?mind|don't)\b", reply.lower()))


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
