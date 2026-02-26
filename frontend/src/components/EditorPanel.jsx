export default function EditorPanel({ filePath, content }) {
  if (!filePath) {
    return (
      <div className="h-full flex items-center justify-center text-[#333] text-sm">
        select a file to view
      </div>
    )
  }

  const lines = (content || "").split("\n")
  const ext = filePath.split(".").pop()?.toLowerCase()

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Tab bar */}
      <div className="h-8 bg-[#161616] border-b border-[#2a2a2a] flex items-center px-3">
        <span className="text-xs text-[#4ade80] bg-[#1a1a1a] border border-[#2a2a2a] px-2 py-0.5 rounded text-[11px]">
          {filePath}
        </span>
      </div>

      {/* Code */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-xs leading-5">
          <tbody>
            {lines.map((line, i) => (
              <tr key={i} className="hover:bg-[#161616] group">
                <td className="w-12 text-right pr-4 text-[#333] group-hover:text-[#555] select-none align-top py-0 leading-5 pl-2 shrink-0">
                  {i + 1}
                </td>
                <td className="pr-6 align-top py-0">
                  <pre className={`font-mono whitespace-pre-wrap break-all ${getColorClass(line, ext)}`}>
                    {line || " "}
                  </pre>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// Very basic syntax coloring by line content
function getColorClass(line, ext) {
  const trimmed = line.trim()

  if (["py"].includes(ext)) {
    if (trimmed.startsWith("#")) return "text-[#6b7280]"
    if (trimmed.startsWith("def ") || trimmed.startsWith("async def ")) return "text-[#60a5fa]"
    if (trimmed.startsWith("class ")) return "text-[#a78bfa]"
    if (trimmed.startsWith("import ") || trimmed.startsWith("from ")) return "text-[#f59e0b]"
    if (trimmed.startsWith("return ")) return "text-[#f87171]"
  }

  if (["js", "jsx", "ts", "tsx"].includes(ext)) {
    if (trimmed.startsWith("//") || trimmed.startsWith("*")) return "text-[#6b7280]"
    if (trimmed.startsWith("import ") || trimmed.startsWith("export ")) return "text-[#f59e0b]"
    if (trimmed.startsWith("const ") || trimmed.startsWith("let ") || trimmed.startsWith("var ")) return "text-[#60a5fa]"
    if (trimmed.startsWith("function ") || trimmed.includes("=>")) return "text-[#60a5fa]"
    if (trimmed.startsWith("return ")) return "text-[#f87171]"
  }

  if (ext === "json") {
    if (trimmed.startsWith('"') && trimmed.includes('":')) return "text-[#4ade80]"
  }

  if (ext === "sql") {
    const keywords = ["CREATE", "SELECT", "INSERT", "UPDATE", "DELETE", "TABLE", "FROM", "WHERE"]
    if (keywords.some(k => trimmed.toUpperCase().startsWith(k))) return "text-[#f59e0b]"
  }

  if (ext === "md") {
    if (trimmed.startsWith("#")) return "text-[#4ade80] font-bold"
    if (trimmed.startsWith("```")) return "text-[#6b7280]"
    if (trimmed.startsWith("-") || trimmed.startsWith("*")) return "text-[#60a5fa]"
  }

  return "text-[#cdd6f4]"
}
