import { useState } from "react"
import type { DesignSession, GenerationMeta } from "../App"

interface Message {
  id: string
  role: "user" | "system" | "error"
  text: string
}

interface Props {
  meta: GenerationMeta
  designSession: DesignSession | null
  onWireframe: (session: DesignSession) => void
}

const STYLE_OPTIONS = [
  { value: "minimalism", label: "Minimalism" },
  { value: "glassmorphism", label: "Glassmorphism" },
  { value: "skeuomorphism", label: "Skeuomorphism" },
  { value: "claymorphism", label: "Claymorphism" },
  { value: "liquid_glass", label: "Liquid Glass" },
  { value: "neo_brutalism", label: "Neo Brutalism" }
]

function createMessage(role: Message["role"], text: string): Message {
  return {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    text
  }
}

function formatBackendError(data: unknown): string {
  if (!data || typeof data !== "object") {
    return "Generation failed"
  }

  const detail = "detail" in data ? (data as { detail?: unknown }).detail : undefined

  if (typeof detail === "string") {
    return detail
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (!item || typeof item !== "object") return String(item)
        const issue = item as { loc?: unknown[]; msg?: string; type?: string }
        const field = Array.isArray(issue.loc) ? issue.loc.join(".") : "request"
        return `${field}: ${issue.msg || issue.type || "Invalid value"}`
      })
      .join("\n")
  }

  return JSON.stringify(data, null, 2)
}

export default function ChatPanel({ meta, designSession, onWireframe }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [selectedStyle, setSelectedStyle] = useState("")
  const [loading, setLoading] = useState(false)

  const pageCount = designSession?.wireframe.pages.length ?? meta.pageCount

  const handleWireframe = async () => {
    const prompt = input.trim()
    if (!prompt || loading) return

    setLoading(true)
    setMessages((prev) => [
      ...prev,
      createMessage("user", prompt),
      createMessage("system", "Creating a wireframe draft. Assets and code will wait for your approval.")
    ])

    try {
      const response = await fetch("/design-preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, selected_style: selectedStyle })
      })

      if (!response.ok) {
        throw new Error(formatBackendError(await response.json()))
      }

      const session = await response.json() as DesignSession
      onWireframe(session)
      setMessages((prev) => [
        ...prev,
        createMessage("system", "Wireframe ready. Review it in the preview panel, then approve it to see asset options.")
      ])
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error"
      setMessages((prev) => [...prev, createMessage("error", message)])
    } finally {
      setLoading(false)
    }
  }

  return (
    <aside className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-white/10 bg-[#171716]/94 shadow-2xl shadow-black/40 backdrop-blur-xl">
      <div className="border-b border-white/10 px-5 py-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-xs font-semibold uppercase tracking-[0.22em] text-[#d3ff72]">Agentic UI</div>
            <h1 className="mt-2 truncate text-xl font-semibold tracking-tight text-[#fffaf0]">Website Generator</h1>
            <p className="mt-1 text-sm text-[#9ba3af]">Previewing generated website builds</p>
          </div>
          <div className={`shrink-0 rounded-full border px-3 py-1 text-xs font-medium ${
            loading
              ? "border-[#d3ff72]/40 bg-[#d3ff72]/10 text-[#edffbd]"
              : "border-white/10 bg-white/5 text-[#aeb6c2]"
          }`}>
            {loading ? "Running" : "Ready"}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 border-b border-white/10 bg-black/14 text-sm">
        <div className="px-4 py-3">
          <div className="text-xs uppercase tracking-[0.14em] text-[#737b87]">Files</div>
          <div className="mt-1 text-lg font-semibold text-[#fffaf0]">{meta.fileCount}</div>
        </div>
        <div className="border-x border-white/10 px-4 py-3">
          <div className="text-xs uppercase tracking-[0.14em] text-[#737b87]">Pages</div>
          <div className="mt-1 text-lg font-semibold text-[#fffaf0]">{pageCount}</div>
        </div>
        <div className="px-4 py-3">
          <div className="text-xs uppercase tracking-[0.14em] text-[#737b87]">Status</div>
          <div className="mt-1 text-lg font-semibold text-[#fffaf0]">{loading ? "Live" : "Idle"}</div>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-6">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
          {messages.length === 0 && (
            <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.04] p-6 shadow-xl shadow-black/20">
              <div className="text-sm uppercase tracking-[0.18em] text-[#7f8792]">Chat</div>
              <h2 className="mt-3 text-2xl font-semibold tracking-tight text-[#fffaf0]">What should we build?</h2>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[#a9b0bb]">
                Create a wireframe first, review it, then approve the design before any assets or final code are generated.
              </p>
            </div>
          )}
          {messages.map((message) => (
            <div
              key={message.id}
              className={[
                "max-w-[78%] rounded-2xl border px-4 py-3 text-sm leading-6 shadow-sm max-sm:max-w-[92%]",
                message.role === "user"
                  ? "ml-auto border-white/12 bg-[#2a2a28] text-[#f7f2e8]"
                  : "",
                message.role === "system"
                  ? "mr-auto border-[#2d5cff]/35 bg-[#222426] text-[#d8dce0]"
                  : "",
                message.role === "error"
                  ? "mr-auto border-[#ff6b6b]/40 bg-[#ff6b6b]/10 text-[#ffd0d0]"
                  : ""
              ].join(" ")}
            >
              {message.text}
            </div>
          ))}
        </div>
      </div>

      <div className="border-t border-white/10 bg-[#171716]/95 px-5 py-4">
        <div className="mx-auto w-full max-w-3xl rounded-3xl border border-white/10 bg-[#252523] p-4 shadow-2xl shadow-black/30">
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            disabled={loading}
            rows={3}
            className="h-24 w-full resize-none border-0 bg-transparent px-1 py-1 text-base leading-7 text-[#f8f4ea] outline-none placeholder:text-[#8d929b] disabled:opacity-60"
            placeholder="Queue follow-up..."
          />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex min-w-0 flex-wrap items-center gap-2">
              <select
                value={selectedStyle}
                onChange={(event) => setSelectedStyle(event.target.value)}
                disabled={loading}
                className="h-9 max-w-[180px] rounded-full border border-white/12 bg-[#1a1b1f] px-3 text-sm font-medium text-[#f8f4ea] outline-none transition focus:border-[#d3ff72]/70 disabled:opacity-60"
              >
                <option value="" disabled>
                  Select style
                </option>
                {STYLE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              onClick={handleWireframe}
              disabled={loading || !input.trim() || !selectedStyle}
              className="h-10 rounded-full bg-[#d3ff72] px-5 text-sm font-semibold text-[#11140d] shadow-lg shadow-[#d3ff72]/10 transition hover:bg-[#e0ff94] hover:shadow-[#d3ff72]/20 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Working..." : "Create wireframe"}
            </button>
          </div>
        </div>
      </div>
    </aside>
  )
}
