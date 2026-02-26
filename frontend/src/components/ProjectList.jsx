import { useState, useEffect, useRef } from "react"

export default function ProjectList({ onGenerate, onOpenProject, isGenerating, messages, ollamaOk }) {
  const [prompt, setPrompt] = useState("")
  const [projects, setProjects] = useState([])
  const messagesEndRef = useRef(null)

  useEffect(() => {
    fetch("http://localhost:8000/projects")
      .then(r => r.json())
      .then(setProjects)
      .catch(() => {})
  }, [isGenerating])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!prompt.trim() || isGenerating) return
    onGenerate(prompt.trim())
    setPrompt("")
  }

  const examples = [
    "build a todo app with user authentication",
    "create a blog with admin panel",
    "make an expense tracker with charts",
    "build a simple ecommerce store",
    "create a restaurant menu and ordering system"
  ]

  return (
    <div className="flex-1 flex flex-col overflow-hidden">

      {messages.length === 0 ? (
        /* Home Screen */
        <div className="flex-1 flex flex-col items-center justify-center px-8 gap-8">

          <div className="text-center">
            <div className="text-5xl font-bold text-[#4ade80] tracking-tight mb-2">OffRepl</div>
            <div className="text-[#555] text-sm">describe your app. get full stack code. no internet needed.</div>
          </div>

          {!ollamaOk && (
            <div className="bg-red-900/20 border border-red-800/50 rounded px-4 py-3 text-sm text-red-400 max-w-lg text-center">
              ⚠ Ollama is not running. Start it with: <code className="bg-red-900/30 px-1 rounded">ollama serve</code>
            </div>
          )}

          {/* Input */}
          <form onSubmit={handleSubmit} className="w-full max-w-2xl">
            <div className="relative">
              <textarea
                value={prompt}
                onChange={e => setPrompt(e.target.value)}
                onKeyDown={e => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault()
                    handleSubmit(e)
                  }
                }}
                placeholder="describe your web app..."
                rows={3}
                className="w-full bg-[#1a1a1a] border border-[#2a2a2a] focus:border-[#4ade80]/50 rounded-lg px-4 py-3 text-sm text-gray-200 placeholder-[#444] resize-none outline-none transition-colors"
              />
              <button
                type="submit"
                disabled={!prompt.trim() || isGenerating || !ollamaOk}
                className="absolute bottom-3 right-3 bg-[#4ade80] text-black text-xs font-bold px-3 py-1.5 rounded disabled:opacity-30 disabled:cursor-not-allowed hover:bg-[#22c55e] transition-colors"
              >
                {isGenerating ? "generating..." : "generate →"}
              </button>
            </div>
          </form>

          {/* Examples */}
          <div className="w-full max-w-2xl">
            <div className="text-[#444] text-xs mb-3">examples</div>
            <div className="flex flex-wrap gap-2">
              {examples.map(ex => (
                <button
                  key={ex}
                  onClick={() => setPrompt(ex)}
                  className="text-xs bg-[#1a1a1a] border border-[#2a2a2a] hover:border-[#4ade80]/30 text-[#666] hover:text-gray-300 px-3 py-1.5 rounded transition-all"
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>

          {/* Recent Projects */}
          {projects.length > 0 && (
            <div className="w-full max-w-2xl">
              <div className="text-[#444] text-xs mb-3">recent projects</div>
              <div className="flex flex-col gap-2">
                {projects.slice(0, 5).map(p => (
                  <button
                    key={p.id}
                    onClick={() => onOpenProject(p)}
                    className="text-left bg-[#1a1a1a] border border-[#2a2a2a] hover:border-[#4ade80]/30 rounded px-4 py-3 transition-all group"
                  >
                    <div className="text-sm text-gray-300 group-hover:text-white truncate">{p.prompt}</div>
                    <div className="text-xs text-[#444] mt-1 flex gap-3">
                      <span>{p.file_count || 0} files</span>
                      <span>{p.tables?.length || 0} tables</span>
                      <span>v{p.version || 1}</span>
                      <span className="ml-auto">{new Date(p.created_at).toLocaleDateString()}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

      ) : (
        /* Generation Progress Screen */
        <div className="flex-1 flex flex-col">
          <div className="flex-1 overflow-y-auto px-8 py-6">
            <div className="max-w-2xl mx-auto flex flex-col gap-3">
              {messages.map(msg => (
                <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`
                    max-w-lg px-4 py-2.5 rounded text-sm
                    ${msg.role === "user"
                      ? "bg-[#4ade80]/10 border border-[#4ade80]/20 text-gray-200"
                      : msg.type === "error"
                        ? "bg-red-900/20 border border-red-800/30 text-red-400"
                        : msg.type === "success"
                          ? "bg-green-900/20 border border-green-800/30 text-green-400"
                          : "bg-[#1a1a1a] border border-[#2a2a2a] text-[#888]"
                    }
                  `}>
                    {msg.type === "status" && (
                      <span className="inline-block w-2 h-2 bg-[#4ade80] rounded-full mr-2 animate-pulse" />
                    )}
                    {msg.text}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input at bottom during generation */}
          {!isGenerating && (
            <div className="border-t border-[#2a2a2a] px-8 py-4">
              <form onSubmit={handleSubmit} className="max-w-2xl mx-auto">
                <div className="flex gap-2">
                  <input
                    value={prompt}
                    onChange={e => setPrompt(e.target.value)}
                    placeholder="describe another app..."
                    className="flex-1 bg-[#1a1a1a] border border-[#2a2a2a] rounded px-3 py-2 text-sm outline-none focus:border-[#4ade80]/50"
                  />
                  <button
                    type="submit"
                    className="bg-[#4ade80] text-black text-xs font-bold px-4 py-2 rounded"
                  >
                    generate
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
