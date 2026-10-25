import { useCallback, useEffect, useState } from "react"
import { Todo, type TodoFilter, type TodoItem } from "@/components/ui/todo-task-management"
import { ChatPane, type View } from "@/components/ChatPane"
import { cn } from "@/lib/utils"

const FILTERS: { value: TodoFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "open", label: "Left" },
  { value: "done", label: "Done" },
]

export default function App() {
  const [todos, setTodos] = useState<TodoItem[]>([])
  const [mode, setMode] = useState("")
  // Display only: which todos to show. Set by a list turn ("what's left?") or the toggle.
  const [filter, setFilter] = useState<TodoFilter>("all")

  // Display only: the backend owns todos and conversation state.
  const refresh = useCallback(async () => {
    const res = await fetch("/todos")
    const data = await res.json()
    setTodos(data.todos)
    setMode(data.mode)
  }, [])

  const onTurn = useCallback(
    (view: View | null) => {
      if (view) setFilter(view)
      refresh()
    },
    [refresh],
  )

  useEffect(() => {
    refresh()
  }, [refresh])

  return (
    <div className="grid h-screen grid-cols-1 overflow-hidden md:grid-cols-[1fr_420px]">
      <main className="overflow-y-auto px-8 pt-20 pb-8">
        <div className="mx-auto mb-6 flex max-w-2xl items-baseline justify-between px-4">
          <h1 className="text-2xl font-semibold">Todos</h1>
          <div className="flex gap-3 text-sm">
            {FILTERS.map((f) => (
              <button
                key={f.value}
                onClick={() => setFilter(f.value)}
                className={cn(
                  "text-muted-foreground transition-colors hover:text-foreground",
                  filter === f.value && "text-foreground underline underline-offset-4",
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
        <Todo todos={todos} filter={filter} />
      </main>
      <ChatPane mode={mode} onTurn={onTurn} />
    </div>
  )
}
