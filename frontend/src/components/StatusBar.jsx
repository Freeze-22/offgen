export default function StatusBar({ project, isRunning, runUrls, isGenerating, fileCount, onRun, onStop }) {
  return (
    <div className="h-8 bg-[#161616] border-t border-[#2a2a2a] flex items-center px-4 gap-4 shrink-0 text-[11px]">

      {/* Project info */}
      {project ? (
        <span className="text-[#555] truncate max-w-xs">
          {project.prompt}
        </span>
      ) : (
        <span className="text-[#333]">no project</span>
      )}

      <span className="text-[#333]">|</span>

      {/* File count */}
      {fileCount > 0 && (
        <span className="text-[#444]">{fileCount} files</span>
      )}

      {/* Generation status */}
      {isGenerating && (
        <span className="text-[#4ade80] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-[#4ade80] rounded-full animate-pulse inline-block" />
          generating...
        </span>
      )}

      {/* Run controls */}
      <div className="ml-auto flex items-center gap-3">
        {runUrls && (
          <>
            <a
              href={runUrls.frontend_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[#4ade80] hover:underline"
            >
              🌐 {runUrls.frontend_url}
            </a>
            <a
              href={runUrls.api_docs_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[#60a5fa] hover:underline"
            >
              📡 api docs
            </a>
          </>
        )}

        {project && !isGenerating && (
          isRunning ? (
            <button
              onClick={onStop}
              className="bg-red-900/20 border border-red-800/30 text-red-400 hover:bg-red-900/40 px-3 py-0.5 rounded transition-all"
            >
              ⏹ stop
            </button>
          ) : (
            <button
              onClick={onRun}
              className="bg-[#4ade80]/10 border border-[#4ade80]/20 text-[#4ade80] hover:bg-[#4ade80]/20 px-3 py-0.5 rounded transition-all"
            >
              ▶ run
            </button>
          )
        )}
      </div>
    </div>
  )
}
