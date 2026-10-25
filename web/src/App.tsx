import { useCallback, useEffect, useState } from "react"
import { Todo, type TodoItem } from "@/components/ui/todo-task-management"
import { ChatPane } from "@/components/ChatPane"

export default function App() {
  const [todos, setTodos] = useState<TodoItem[]>([])
  const [mode, setMode] = useState("")

  // Display only: the backend owns todos and conversation state.
  const refresh = useCallback(async () => {
    const res = await fetch("/todos")
    const data = await res.json()
    setTodos(data.todos)
    setMode(data.mode)
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return (
    <div className="grid h-screen grid-cols-1 md:grid-cols-[1fr_420px]">
      <main className="overflow-y-auto px-8 pt-20 pb-8">
        <h1 className="mx-auto mb-6 max-w-2xl px-4 text-2xl font-semibold">Todos</h1>
        <Todo todos={todos} />
      </main>
      <ChatPane mode={mode} onTurn={refresh} />
    </div>
  )
}
