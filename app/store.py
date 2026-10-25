import json
import sqlite3

from app.state import State

CONVERSATION_ID = 1  # single conversation for now; per-user conversation_id in production


class Store:
    def __init__(self, path: str = "todos.db"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS todos ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL, "
            "completed INTEGER NOT NULL DEFAULT 0, "
            "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS conversation_state ("
            "id INTEGER PRIMARY KEY, last_referenced_id INTEGER, pending_json TEXT)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS messages ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT NOT NULL, content TEXT NOT NULL, "
            "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        self.db.commit()

    def load_state(self) -> State:
        row = self.db.execute(
            "SELECT last_referenced_id, pending_json FROM conversation_state WHERE id = ?",
            (CONVERSATION_ID,),
        ).fetchone()
        history = [{"role": r["role"], "content": r["content"]}
                   for r in self.db.execute("SELECT role, content FROM messages ORDER BY id")]
        if row is None:
            return State(history=history)
        pending = json.loads(row["pending_json"]) if row["pending_json"] else None
        return State(history=history, last_referenced_id=row["last_referenced_id"], pending=pending)

    def save_state(self, state: State, new_messages: list[dict]) -> None:
        """Upsert the conversation row and append this turn's messages, in one commit."""
        self.db.execute(
            "INSERT INTO conversation_state (id, last_referenced_id, pending_json) VALUES (?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET last_referenced_id = excluded.last_referenced_id, "
            "pending_json = excluded.pending_json",
            (CONVERSATION_ID, state.last_referenced_id,
             json.dumps(state.pending) if state.pending else None),
        )
        self.db.executemany("INSERT INTO messages (role, content) VALUES (?, ?)",
                            [(m["role"], m["content"]) for m in new_messages])
        self.db.commit()

    def list(self) -> list[dict]:
        rows = self.db.execute("SELECT id, text, completed FROM todos ORDER BY id").fetchall()
        return [{"id": r["id"], "text": r["text"], "completed": bool(r["completed"])} for r in rows]

    def get(self, todo_id: int) -> dict | None:
        return next((t for t in self.list() if t["id"] == todo_id), None)

    def add(self, text: str) -> dict:
        cur = self.db.execute("INSERT INTO todos (text) VALUES (?)", (text,))
        self.db.commit()
        return self.get(cur.lastrowid)

    def update(self, todo_id: int, text: str) -> None:
        self.db.execute("UPDATE todos SET text = ? WHERE id = ?", (text, todo_id))
        self.db.commit()

    def complete(self, todo_id: int) -> None:
        self.db.execute("UPDATE todos SET completed = 1 WHERE id = ?", (todo_id,))
        self.db.commit()

    def delete(self, todo_id: int) -> None:
        self.db.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        self.db.commit()
