import { useState, useEffect, useRef } from "react"
import FileTree from "./components/FileTree"
import EditorPanel from "./components/EditorPanel"
import ChatPanel from "./components/ChatPanel"
import StatusBar from "./components/StatusBar"
import ProjectList from "./components/ProjectList"

export default function App() {
  const [view, setView] = useState("home") // home | editor
  const [currentProject, setCurrentProject] = useState(null)
  const [files, setFiles] = useState([])
  const [activeFile, setActiveFile] = useState(null)
  const [activeFileContent, setActiveFileContent] = useState("")
  const [isGenerating, setIsGenerating] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [runUrls, setRunUrls] = useState(null)
  const [messages, setMessages] = useState([])
  const [ollamaOk, setOllamaOk] = useState(null)
  const wsRef = useRef(null)

  // Check Ollama on load
  useEffect(() => {
    fetch("http://localhost:8000/health")
      .then(r => r.json())
      .then(d => setOllamaOk(d.ollama))
      .catch(() => setOllamaOk(false))
  }, [])

  const addMessage = (role, text, type = "text") => {
    setMessages(prev => [...prev, {
      id: Date.now(),
      role,
      text,
      type,
      time: new Date().toLocaleTimeString()
    }])
  }

  const handleGenerate = async (prompt) => {
    setIsGenerating(true)
    setMessages([])
    addMessage("user", prompt)
    addMessage("assistant", "🤔 Starting...", "status")

    const ws = new WebSocket("ws://localhost:8000/ws/generate")
    wsRef.current = ws

    ws.onmessage = async (e) => {
      const data = JSON.parse(e.data)
      const { event, message } = data

      if (event === "start") {
        setCurrentProject({ id: data.data.project_id, prompt })
        setMessages(prev => prev.map((m, i) =>
          i === prev.length - 1 ? { ...m, text: "🚀 " + message } : m
        ))
      } else if (["thinking", "interview", "modules", "stage", "writing"].includes(event)) {
        setMessages(prev => {
          const last = prev[prev.length - 1]
          if (last?.role === "assistant" && last?.type === "status") {
            return [...prev.slice(0, -1), { ...last, text: getEmoji(event) + " " + message }]
          }
          return [...prev, { id: Date.now(), role: "assistant", text: getEmoji(event) + " " + message, type: "status" }]
        })
      } else if (event === "complete") {
        setIsGenerating(false)
        setFiles(data.data.files || [])
        setView("editor")
        addMessage("assistant", `✅ Done! ${data.data.file_count} files generated.`, "success")

        // Load first file
        if (data.data.files?.length > 0) {
          const firstFile = data.data.files[0]
          handleFileSelect(data.data.project_id, firstFile.path)
        }
      } else if (event === "error") {
        setIsGenerating(false)
        addMessage("assistant", "❌ " + message, "error")
      }
    }

    ws.onclose = () => setIsGenerating(false)
    ws.onerror = () => {
      setIsGenerating(false)
      addMessage("assistant", "❌ Connection failed. Is the backend running?", "error")
    }

    ws.onopen = () => ws.send(JSON.stringify({ prompt }))
  }

  const handleIterate = async (change) => {
    if (!currentProject) return
    setIsGenerating(true)
    addMessage("user", change)
    addMessage("assistant", "🔍 Analyzing change...", "status")

    const ws = new WebSocket(`ws://localhost:8000/ws/iterate/${currentProject.id}`)
    wsRef.current = ws

    ws.onmessage = async (e) => {
      const data = JSON.parse(e.data)
      const { event, message } = data

      if (["analyzing", "analysis", "generating"].includes(event)) {
        setMessages(prev => {
          const last = prev[prev.length - 1]
          if (last?.role === "assistant" && last?.type === "status") {
            return [...prev.slice(0, -1), { ...last, text: "🔄 " + message }]
          }
          return [...prev, { id: Date.now(), role: "assistant", text: "🔄 " + message, type: "status" }]
        })
      } else if (event === "complete") {
        setIsGenerating(false)
        setFiles(data.data.files || [])
        addMessage("assistant", `✅ ${message}`, "success")

        // Reload active file if it changed
        if (activeFile && data.data.changed_files?.includes(activeFile)) {
          handleFileSelect(currentProject.id, activeFile)
        }
      } else if (event === "error") {
        setIsGenerating(false)
        addMessage("assistant", "❌ " + message, "error")
      }
    }

    ws.onclose = () => setIsGenerating(false)
    ws.onopen = () => ws.send(JSON.stringify({ change }))
  }

  const handleFileSelect = async (projectId, filePath) => {
    const pid = projectId || currentProject?.id
    if (!pid) return

    setActiveFile(filePath)
    const res = await fetch(`http://localhost:8000/projects/${pid}/files/${filePath}`)
    if (res.ok) {
      const data = await res.json()
      setActiveFileContent(data.content)
    }
  }

  const handleRun = async () => {
    if (!currentProject) return
    setIsRunning(true)
    addMessage("assistant", "🐳 Starting your project...", "status")

    const ws = new WebSocket(`ws://localhost:8000/ws/run/${currentProject.id}`)

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.event === "running" && data.data) {
        setRunUrls(data.data)
        addMessage("assistant", `🌐 Running at ${data.data.frontend_url}`, "success")
      } else if (data.event === "error") {
        setIsRunning(false)
        addMessage("assistant", "❌ " + data.message, "error")
      }
    }

    ws.onopen = () => {}
  }

  const handleStop = async () => {
    if (!currentProject) return
    await fetch(`http://localhost:8000/projects/${currentProject.id}/stop`, { method: "POST" })
    setIsRunning(false)
    setRunUrls(null)
    addMessage("assistant", "⏹ Project stopped", "status")
  }

  const handleOpenProject = async (project) => {
    setCurrentProject(project)
    const res = await fetch(`http://localhost:8000/projects/${project.id}/files`)
    const files = await res.json()
    setFiles(files)
    setView("editor")
    setMessages([{ id: 1, role: "assistant", text: `📂 Opened: ${project.prompt}`, type: "success", time: "" }])
  }

  return (
    <div className="h-screen flex flex-col bg-[#0d0d0d] text-gray-100 font-mono overflow-hidden">

      {/* Top Bar */}
      <div className="h-10 bg-[#161616] border-b border-[#2a2a2a] flex items-center px-4 gap-4 shrink-0">
        <span className="text-[#4ade80] font-bold text-sm tracking-widest">OFFREPL</span>
        <span className="text-[#3d3d3d] text-xs">|</span>
        <span className="text-[#555] text-xs">offline ai project generator</span>

        <div className="ml-auto flex items-center gap-3">
          {ollamaOk === false && (
            <span className="text-red-400 text-xs">⚠ ollama not running</span>
          )}
          {ollamaOk === true && (
            <span className="text-green-400 text-xs">● ollama ready</span>
          )}

          {view === "editor" && (
            <button
              onClick={() => setView("home")}
              className="text-xs text-[#555] hover:text-gray-300 transition-colors"
            >
              ← projects
            </button>
          )}
        </div>
      </div>

      {/* Main Content */}
      {view === "home" ? (
        <ProjectList
          onGenerate={handleGenerate}
          onOpenProject={handleOpenProject}
          isGenerating={isGenerating}
          messages={messages}
          ollamaOk={ollamaOk}
        />
      ) : (
        <div className="flex flex-1 overflow-hidden">
          {/* File Tree */}
          <div className="w-56 border-r border-[#2a2a2a] overflow-y-auto shrink-0">
            <FileTree
              files={files}
              activeFile={activeFile}
              onSelect={(path) => handleFileSelect(currentProject?.id, path)}
            />
          </div>

          {/* Editor */}
          <div className="flex-1 overflow-hidden">
            <EditorPanel
              filePath={activeFile}
              content={activeFileContent}
            />
          </div>

          {/* Chat Panel */}
          <div className="w-80 border-l border-[#2a2a2a] flex flex-col shrink-0">
            <ChatPanel
              messages={messages}
              isGenerating={isGenerating}
              onSend={handleIterate}
              currentProject={currentProject}
            />
          </div>
        </div>
      )}

      {/* Status Bar */}
      <StatusBar
        project={currentProject}
        isRunning={isRunning}
        runUrls={runUrls}
        isGenerating={isGenerating}
        fileCount={files.length}
        onRun={handleRun}
        onStop={handleStop}
      />
    </div>
  )
}

function getEmoji(event) {
  const map = {
    thinking: "🧠",
    interview: "📋",
    modules: "📦",
    stage: "⚙️",
    writing: "✍️",
    running: "🚀",
  }
  return map[event] || "•"
}
