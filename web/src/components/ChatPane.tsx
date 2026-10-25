import { useEffect, useRef, useState } from "react"
import { cn } from "@/lib/utils"

type TraceEvent = { event: string } & Record<string, unknown>
type Message = { role: "user" | "assistant"; text: string; trace?: TraceEvent[]; error?: boolean }

export interface ChatPaneProps {
  mode: string
  onTurn: () => void
}

function formatEvent(e: TraceEvent) {
  const data = Object.entries(e)
    .filter(([k]) => k !== "event")
    .map(([k, v]) => `${k}=${typeof v === "string" ? v : JSON.stringify(v)}`)
    .join(" ")
  return { name: e.event, data }
}

function Trace({ trace }: { trace: TraceEvent[] }) {
  const skill = trace.find((e) => e.event === "skill_loaded")?.skill as string | undefined
  const last = trace[trace.length - 1]?.event
  return (
    <details className="mt-2 text-xs text-muted-foreground">
      <summary className="cursor-pointer select-none hover:text-foreground">
        trace · {skill ? `skill: ${skill}` : "no skill loaded"} · {last}
      </summary>
      <div className="mt-1 space-y-0.5 border-l border-border pl-3 font-mono">
        {trace.map((e, i) => {
          const { name, data } = formatEvent(e)
          return (
            <div key={i}>
              <span className={cn(name === "failed" && "text-destructive", name === "clarified" && "text-amber-600")}>
                {name}
              </span>{" "}
              {data}
            </div>
          )
        })}
      </div>
    </details>
  )
}

export function ChatPane({ mode, onTurn }: ChatPaneProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [busy, setBusy] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), [messages, busy])

  const send = async () => {
    const text = input.trim()
    if (!text || busy) return
    setInput("")
    setMessages((m) => [...m, { role: "user", text }])
    setBusy(true)
    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setMessages((m) => [...m, { role: "assistant", text: data.reply, trace: data.trace }])
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", text: `Request failed: ${err}`, error: true }])
    } finally {
      setBusy(false)
      onTurn()
    }
  }

  return (
    <aside className="flex h-full flex-col border-l border-border bg-muted/40">
      <header className="flex items-center justify-between border-b border-border px-5 py-3">
        <span className="text-sm font-medium">Chat</span>
        <span className="rounded border border-border bg-background px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
          {mode || "…"}
        </span>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
        {messages.length === 0 && (
          <div className="space-y-1 text-sm text-muted-foreground">
            <p>Try:</p>
            <p className="font-mono text-xs">Add a task to send the quote</p>
            <p className="font-mono text-xs">Change that to send the revised quote</p>
            <p className="font-mono text-xs">delete the quote</p>
          </div>
        )}
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="flex justify-end">
              <div className="max-w-[85%] rounded-lg bg-background px-3 py-2 text-sm shadow-sm ring-1 ring-border">
                {m.text}
              </div>
            </div>
          ) : (
            <div key={i} className="text-sm">
              <div className={cn("whitespace-pre-wrap", m.error && "text-destructive")}>{m.text}</div>
              {m.trace && <Trace trace={m.trace} />}
            </div>
          ),
        )}
        {busy && <div className="text-sm text-muted-foreground">Thinking…</div>}
        <div ref={endRef} />
      </div>

      <div className="border-t border-border p-3">
        <div className="flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 focus-within:ring-1 focus-within:ring-foreground/20">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder="Ask to add, change, complete or delete…"
            className="flex-1 bg-transparent text-sm placeholder:text-muted-foreground focus:outline-none"
            disabled={busy}
            autoFocus
          />
          <button
            onClick={send}
            disabled={busy || !input.trim()}
            className="text-sm font-medium text-foreground disabled:opacity-30"
          >
            Send
          </button>
        </div>
      </div>
    </aside>
  )
}
