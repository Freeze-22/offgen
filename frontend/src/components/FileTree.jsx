import { useState } from "react"

const FILE_ICONS = {
  py: "🐍",
  js: "📜",
  jsx: "⚛️",
  ts: "📘",
  tsx: "⚛️",
  json: "📋",
  md: "📄",
  yml: "⚙️",
  yaml: "⚙️",
  css: "🎨",
  html: "🌐",
  sql: "🗄️",
  txt: "📝",
  sh: "💻",
  env: "🔐",
}

function getIcon(filename) {
  const ext = filename.split(".").pop()?.toLowerCase()
  return FILE_ICONS[ext] || "📄"
}

function buildTree(files) {
  const tree = {}

  for (const file of files) {
    const parts = file.path.split("/")
    let current = tree

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      if (i === parts.length - 1) {
        current[part] = { __file: true, path: file.path }
      } else {
        if (!current[part]) current[part] = {}
        current = current[part]
      }
    }
  }

  return tree
}

function TreeNode({ name, node, depth, onSelect, activeFile }) {
  const [open, setOpen] = useState(depth < 2)
  const isFile = node.__file

  if (isFile) {
    return (
      <button
        onClick={() => onSelect(node.path)}
        className={`
          w-full text-left flex items-center gap-1.5 px-2 py-0.5 text-xs
          hover:bg-[#2a2a2a] transition-colors rounded
          ${activeFile === node.path ? "bg-[#2a2a2a] text-[#4ade80]" : "text-[#888] hover:text-gray-300"}
        `}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        <span>{getIcon(name)}</span>
        <span className="truncate">{name}</span>
      </button>
    )
  }

  const children = Object.entries(node).sort(([a, av], [b, bv]) => {
    // Folders first
    const aIsFile = av.__file
    const bIsFile = bv.__file
    if (aIsFile && !bIsFile) return 1
    if (!aIsFile && bIsFile) return -1
    return a.localeCompare(b)
  })

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left flex items-center gap-1.5 px-2 py-0.5 text-xs text-[#666] hover:text-gray-400 transition-colors"
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        <span>{open ? "▾" : "▸"}</span>
        <span>📁</span>
        <span>{name}</span>
      </button>
      {open && children.map(([childName, childNode]) => (
        <TreeNode
          key={childName}
          name={childName}
          node={childNode}
          depth={depth + 1}
          onSelect={onSelect}
          activeFile={activeFile}
        />
      ))}
    </div>
  )
}

export default function FileTree({ files, activeFile, onSelect }) {
  const tree = buildTree(files)

  return (
    <div className="py-2">
      <div className="px-3 py-1 text-[10px] text-[#444] uppercase tracking-widest mb-1">
        Explorer
      </div>
      {Object.entries(tree).map(([name, node]) => (
        <TreeNode
          key={name}
          name={name}
          node={node}
          depth={0}
          onSelect={onSelect}
          activeFile={activeFile}
        />
      ))}
    </div>
  )
}
