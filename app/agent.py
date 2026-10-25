from app.skills import load_catalog, load_skill
from app.state import State
from app.store import Store
from app.trace import Trace
from app.validate import PRONOUNS, check_args, find_duplicate, match, resolve_choice

HELP = "I can add, list, update, complete or delete todos. Try \"add send the quote\"."


class Agent:
    def __init__(self, llm, store: Store):
        self.llm = llm
        self.store = store
        self.state: State = store.load_state()

    def turn(self, message: str) -> tuple[str, list[dict]]:
        # Conversation state lives in SQLite: load it, run the turn, save it.
        self.state = self.store.load_state()
        trace = Trace()
        reply = self._turn(message, trace)
        new = [{"role": "user", "content": message}, {"role": "assistant", "content": reply}]
        self.state.history += new
        self.store.save_state(self.state, new)
        return reply, trace.events

    def _turn(self, message: str, trace: Trace) -> str:
        if self.state.pending:
            pending, self.state.pending = self.state.pending, None
            candidates = [t for t in self.store.list() if t["id"] in pending["candidate_ids"]]
            choice = resolve_choice(message, candidates)
            if choice:
                if dup := self.duplicate(pending["skill"], pending["args"], choice, trace):
                    return dup
                trace.emit("validated", skill=pending["skill"], todo_id=choice["id"], via="clarification")
                return self.execute(pending["skill"], pending["args"], choice, trace)
            # Not an answer to the question: drop it and handle the message normally.

        try:
            # 1. route(): the model sees the catalog only
            catalog = load_catalog()
            names = [s["name"] for s in catalog]
            trace.emit("catalog_shown", skills=names)
            name = self.llm.route(catalog, message, self.state.history)
            if name not in names:
                trace.emit("failed", reason=f"no skill chosen ({name!r})")
                return f"Sorry, I didn't understand that. {HELP}"

            # 2. act(): load that one skill file, model proposes a tool call
            skill = load_skill(name)
            trace.emit("skill_loaded", skill=name, tool=skill["tool"]["name"])
            args = self.llm.act(skill, message)
            trace.emit("proposed", tool=skill["tool"]["name"], args=args)
        except Exception as e:  # model/network errors: report, change nothing
            trace.emit("failed", reason=f"model error: {type(e).__name__}: {str(e)[:200]}")
            return f"The model call failed ({type(e).__name__}). Nothing was changed."

        # 3. check(): code decides
        return self.check(skill, args, trace)

    def check(self, skill: dict, args: dict, trace: Trace) -> str:
        name = skill["name"]
        errors = check_args(skill["tool"], args)
        if errors:
            trace.emit("failed", reason="; ".join(errors))
            return f"I couldn't {name} that: {'; '.join(errors)}. Nothing was changed."
        if "target" not in args:
            if dup := self.duplicate(name, args, None, trace):
                return dup
            trace.emit("validated", skill=name)
            return self.execute(name, args, None, trace)

        target = args["target"].strip()
        todos = self.store.list()
        matches = match(target, todos, self.state.last_referenced_id)
        if not matches:
            if target.lower() in PRONOUNS:
                # "it" points at nothing (e.g. after a restart or a delete): ask instead of failing.
                candidates = [t for t in todos if not t["completed"]] or todos
                if candidates:
                    return self.clarify(name, args, candidates, trace,
                                        f"Which todo do you mean by \"{target}\"?", reason="unresolved pronoun")
                trace.emit("failed", reason="pronoun with no todos", target=target)
                return f"I'm not sure which todo \"{target}\" means. Nothing was changed."
            trace.emit("failed", reason="no match", target=target)
            return f"No todo matches \"{target}\". Nothing was changed."
        if len(matches) > 1:
            return self.clarify(name, args, matches, trace,
                                f"\"{target}\" matches {len(matches)} todos. Which one?", reason="ambiguous")
        if dup := self.duplicate(name, args, matches[0], trace):
            return dup
        trace.emit("validated", skill=name, todo_id=matches[0]["id"])
        return self.execute(name, args, matches[0], trace)

    def clarify(self, name: str, args: dict, candidates: list[dict], trace: Trace, question: str, reason: str) -> str:
        """Ask which todo, change nothing; the next turn may answer via state.pending."""
        ids = [c["id"] for c in candidates]
        self.state.pending = {"skill": name, "args": args, "candidate_ids": ids}
        trace.emit("clarified", reason=reason, target=args["target"], candidates=ids)
        options = "\n".join(f"  {i}. {c['text']}" for i, c in enumerate(candidates, 1))
        return f"{question}\n{options}\nReply with a number."

    def duplicate(self, name: str, args: dict, todo: dict | None, trace: Trace) -> str | None:
        """Block add/update that would create a second open todo with the same text."""
        if name not in ("add", "update"):
            return None
        existing = find_duplicate(args["text"], self.store.list(), exclude_id=todo["id"] if todo else None)
        if existing is None:
            return None
        self.state.last_referenced_id = existing["id"]
        trace.emit("failed", reason="duplicate", todo_id=existing["id"])
        return f"\"{existing['text']}\" is already on your list. Nothing was changed."

    def execute(self, name: str, args: dict, todo: dict | None, trace: Trace) -> str:
        if name == "add":
            new = self.store.add(args["text"].strip())
            self.state.last_referenced_id = new["id"]
            trace.emit("executed", action="add", todo_id=new["id"])
            return f"Added \"{new['text']}\"."
        if name == "list":
            todos = self.store.list()
            if args["status"] != "all":
                todos = [t for t in todos if t["completed"] == (args["status"] == "done")]
            trace.emit("executed", action="list", count=len(todos))
            if not todos:
                return "No todos." if args["status"] == "all" else f"No {args['status']} todos."
            return "\n".join(f"{'[x]' if t['completed'] else '[ ]'} {t['text']}" for t in todos)

        self.state.last_referenced_id = todo["id"]
        if name == "update":
            self.store.update(todo["id"], args["text"].strip())
            trace.emit("executed", action="update", todo_id=todo["id"])
            return f"Changed \"{todo['text']}\" to \"{args['text'].strip()}\"."
        if name == "complete":
            if todo["completed"]:
                trace.emit("failed", reason="already completed", todo_id=todo["id"])
                return f"\"{todo['text']}\" is already done. Nothing was changed."
            self.store.complete(todo["id"])
            trace.emit("executed", action="complete", todo_id=todo["id"])
            return f"Marked \"{todo['text']}\" as done."
        if name == "delete":
            self.store.delete(todo["id"])
            self.state.last_referenced_id = None
            trace.emit("executed", action="delete", todo_id=todo["id"])
            return f"Deleted \"{todo['text']}\"."
        trace.emit("failed", reason=f"unknown skill {name}")
        return "Something went wrong. Nothing was changed."
