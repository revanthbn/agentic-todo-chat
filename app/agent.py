from app.skills import load_catalog, load_skill
from app.state import State
from app.store import Store
from app.trace import Trace
from app.validate import PRONOUNS, check_args, match, resolve_choice

HELP = "I can add, list, update, complete or delete todos. Try \"add send the quote\"."


class Agent:
    def __init__(self, llm, store: Store, state: State | None = None):
        self.llm = llm
        self.store = store
        self.state = state or State()

    def turn(self, message: str) -> tuple[str, list[dict]]:
        trace = Trace()
        reply = self._turn(message, trace)
        self.state.history += [{"role": "user", "content": message}, {"role": "assistant", "content": reply}]
        return reply, trace.events

    def _turn(self, message: str, trace: Trace) -> str:
        if self.state.pending:
            pending, self.state.pending = self.state.pending, None
            candidates = [t for t in self.store.list() if t["id"] in pending["candidate_ids"]]
            choice = resolve_choice(message, candidates)
            if choice:
                trace.emit("validated", skill=pending["skill"], todo_id=choice["id"], via="clarification")
                return self.execute(pending["skill"], pending["args"], choice, trace)
            # Not an answer to the question: drop it and handle the message normally.

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

        # 3. check(): code decides
        return self.check(skill, args, trace)

    def check(self, skill: dict, args: dict, trace: Trace) -> str:
        name = skill["name"]
        errors = check_args(skill["tool"], args)
        if errors:
            trace.emit("failed", reason="; ".join(errors))
            return f"I couldn't {name} that: {'; '.join(errors)}. Nothing was changed."
        if "target" not in args:
            trace.emit("validated", skill=name)
            return self.execute(name, args, None, trace)

        target = args["target"].strip()
        matches = match(target, self.store.list(), self.state.last_referenced_id)
        if not matches:
            if target.lower() in PRONOUNS:
                trace.emit("failed", reason="pronoun with no earlier todo", target=target)
                return f"I'm not sure which todo \"{target}\" means. Nothing was changed."
            trace.emit("failed", reason="no match", target=target)
            return f"No todo matches \"{target}\". Nothing was changed."
        if len(matches) > 1:
            self.state.pending = {"skill": name, "args": args, "candidate_ids": [m["id"] for m in matches]}
            trace.emit("clarified", target=target, candidates=[m["id"] for m in matches])
            options = "\n".join(f"  {i}. {m['text']}" for i, m in enumerate(matches, 1))
            return f"\"{target}\" matches {len(matches)} todos. Which one?\n{options}\nReply with a number."
        trace.emit("validated", skill=name, todo_id=matches[0]["id"])
        return self.execute(name, args, matches[0], trace)

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
