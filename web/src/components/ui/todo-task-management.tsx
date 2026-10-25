// Adapted from docs/design/todo-component.md. Read-only: the chat is the only
// write path, so add/edit/toggle/delete/clear-completed were removed.
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"

export interface TodoItem {
  id: number
  text: string
  completed: boolean
}

export type TodoFilter = "all" | "open" | "done"

export interface TodoProps {
  todos: TodoItem[]
  filter?: TodoFilter
  className?: string
}

const EMPTY: Record<TodoFilter, string> = {
  all: "No todos yet. Ask the chat to add one.",
  open: "Nothing left. Everything is done.",
  done: "Nothing done yet.",
}

export function Todo({ todos, filter = "all", className }: TodoProps) {
  const shown = filter === "all" ? todos : todos.filter((t) => t.completed === (filter === "done"))
  return (
    <div className={cn("w-full max-w-2xl mx-auto relative", className)}>
      <div className="divide-y divide-border relative border-y border-border">
        <AnimatePresence mode="popLayout" initial={false}>
          {shown.map((todo) => (
            <motion.div
              key={todo.id}
              layout
              initial={{ opacity: 0, y: -12 }}
              animate={{ opacity: 1, y: 0, transition: { duration: 0.3, ease: [0.4, 0, 0.2, 1] } }}
              exit={{
                x: -500,
                opacity: 0,
                height: 0,
                transition: {
                  x: { duration: 0.3, ease: [0.4, 0, 1, 1] },
                  opacity: { duration: 0.2 },
                  height: { duration: 0.2, delay: 0.3 },
                },
              }}
              className="flex items-center gap-0 overflow-hidden"
            >
              <div className="flex items-center justify-center w-12 h-12 border-r border-border">
                <div
                  className={cn(
                    "w-4 h-4 border border-foreground transition-all duration-300",
                    todo.completed && "bg-foreground",
                  )}
                />
              </div>
              <div className="flex-1 px-4 py-3">
                <span
                  className={cn(
                    "text-foreground transition-all duration-300",
                    todo.completed && "opacity-40 line-through decoration-foreground/40",
                  )}
                >
                  {todo.text}
                </span>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        {shown.length === 0 && (
          <div className="px-4 py-6 text-sm text-muted-foreground">
            {EMPTY[todos.length === 0 ? "all" : filter]}
          </div>
        )}
      </div>

      {todos.length > 0 && (
        <div className="px-4 py-3 text-xs text-muted-foreground">
          {todos.filter((t) => !t.completed).length} of {todos.length} tasks remaining
        </div>
      )}
    </div>
  )
}
