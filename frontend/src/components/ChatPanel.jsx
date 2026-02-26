import { useState, useRef, useEffect } from "react"

export default function ChatPanel({ messages, isGenerating, onSend, currentProject }) {
  const [input, setInput] = useState("")
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSend = (e) => {
    e.preventDefault()
    if (!input.trim() || isGenerating || !currentProject) return
    onSend(input.trim())
    setInput("")
  }

  const suggestions = [
    "add dark mode",
    "add user authentication",
    "add search functionality",
    "add email notifications",
    "add pagination",
    "improve the UI design",
  ]

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-8 bg-[#161616] border-b border-[#2a2a2a] flex items-center px-3">
        <span className="text-[10px] text-[#444] uppercase tracking-widest">Chat / Iterate</span>
        {currentProject && (
          <span className="ml-auto text-[10px] text-[#333]">v{currentProject.version || 1}</span>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
        {messages.length === 0 && (
          <div className="text-[#333] text-xs text-center mt-4">
            ask me to modify your project
          </div>
        )}

        {messages.map(msg => (
          <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`
              max-w-[85%] px-3 py-2 rounded text-xs leading-relaxed
              ${msg.role === "user"
                ? "bg-[#4ade80]/10 border border-[#4ade80]/20 text-gray-300"
                : msg.type === "error"
                  ? "bg-red-900/20 border border-red-800/30 text-red-400"
                  : msg.type === "success"
                    ? "bg-green-900/20 border border-green-800/30 text-green-400"
                    : "bg-[#1a1a1a] border border-[#2a2a2a] text-[#777]"
              }
            `}>
              {msg.type === "status" && (
                <span className="inline-block w-1.5 h-1.5 bg-[#4ade80] rounded-full mr-1.5 animate-pulse" />
              )}
              {msg.text}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {/* Suggestions */}
      {!isGenerating && currentProject && messages.length < 2 && (
        <div className="px-3 pb-2">
          <div className="text-[10px] text-[#333] mb-2">suggestions</div>
          <div className="flex flex-wrap gap-1">
            {suggestions.map(s => (
              <button
                key={s}
                onClick={() => setInput(s)}
                className="text-[10px] bg-[#1a1a1a] border border-[#2a2a2a] hover:border-[#4ade80]/30 text-[#555] hover:text-gray-400 px-2 py-1 rounded transition-all"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t border-[#2a2a2a] p-3">
        <form onSubmit={handleSend} className="flex flex-col gap-2">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                handleSend(e)
              }
            }}
            placeholder={currentProject ? "what to change..." : "generate a project first"}
            disabled={!currentProject || isGenerating}
            rows={2}
            className="w-full bg-[#1a1a1a] border border-[#2a2a2a] focus:border-[#4ade80]/50 rounded px-3 py-2 text-xs text-gray-300 placeholder-[#333] resize-none outline-none disabled:opacity-30 transition-colors"
          />
          <button
            type="submit"
            disabled={!input.trim() || isGenerating || !currentProject}
            className="w-full bg-[#4ade80]/10 hover:bg-[#4ade80]/20 border border-[#4ade80]/20 text-[#4ade80] text-xs py-1.5 rounded disabled:opacity-30 disabled:cursor-not-allowed transition-all"
          >
            {isGenerating ? "working..." : "apply change →"}
          </button>
        </form>
      </div>
    </div>
  )
}
