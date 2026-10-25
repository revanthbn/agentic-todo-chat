import sqlite3


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
