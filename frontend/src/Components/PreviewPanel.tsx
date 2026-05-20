import { useEffect, useMemo } from "react"
import Editor from "@monaco-editor/react"

import type { GenerationMeta } from "../App"
import { buildPreviewHtml } from "../lib/previewEngine"
import { usePreviewStore } from "../store/previewStore"

interface Props {
  meta: GenerationMeta
}

function languageForFile(path: string): string {
  if (path.endsWith(".json")) return "json"
  if (path.endsWith(".css")) return "css"
  if (path.endsWith(".html")) return "html"
  if (path.endsWith(".ts") || path.endsWith(".tsx")) return "typescript"
  return "javascript"
}

export default function PreviewPanel({ meta }: Props) {
  const {
    files,
    selectedFile,
    view,
    previewHtml,
    buildStatus,
    buildError,
    setSelectedFile,
    setView,
    updateFile,
    setPreviewHtml,
    setBuildStatus,
    setBuildError,
  } = usePreviewStore((state) => state)

  const fileNames = useMemo(() => Object.keys(files), [files])
  const hasFiles = fileNames.length > 0

  useEffect(() => {
    if (!hasFiles) {
      setPreviewHtml("")
      setBuildStatus("idle")
      setBuildError("")
      return
    }

    let cancelled = false

    async function runBuild() {
      setBuildStatus("building")
      setBuildError("")

      try {
        const html = await buildPreviewHtml(files)
        if (cancelled) return
        setPreviewHtml(html)
        setBuildStatus("ready")
      } catch (error) {
        if (cancelled) return
        const message = error instanceof Error ? error.message : String(error)
        setPreviewHtml("")
        setBuildStatus("error")
        setBuildError(message)
      }
    }

    void runBuild()

    return () => {
      cancelled = true
    }
  }, [files, hasFiles, setBuildError, setBuildStatus, setPreviewHtml])

  return (
    <section className="min-h-0 min-w-0 bg-[#0d0e11]">
      <header className="flex h-16 items-center justify-between border-b border-[#2a2c31] px-5">
        <div className="min-w-0">
          <div className="truncate text-sm text-[#8f969f]">{meta.lastPrompt || "No generation yet"}</div>
          <div className="mt-1 flex items-center gap-3 text-sm font-medium text-[#f8f4ea]">
            <span>{hasFiles ? `${meta.fileCount} files ready` : "Preview waiting for generated files"}</span>
            <span className="text-[#8f969f]">
              {buildStatus === "building" && "Building preview"}
              {buildStatus === "ready" && "Preview ready"}
              {buildStatus === "error" && "Preview failed"}
              {buildStatus === "idle" && !hasFiles && "Idle"}
            </span>
          </div>
        </div>

        <div className="flex rounded-md border border-[#2a2c31] bg-[#16171b] p-1">
          <button
            type="button"
            onClick={() => setView("preview")}
            className={`rounded px-4 py-2 text-sm transition ${
              view === "preview" ? "bg-[#d3ff72] text-[#12140f]" : "text-[#c2c7ce]"
            }`}
          >
            Preview
          </button>
          <button
            type="button"
            onClick={() => setView("code")}
            className={`rounded px-4 py-2 text-sm transition ${
              view === "code" ? "bg-[#d3ff72] text-[#12140f]" : "text-[#c2c7ce]"
            }`}
          >
            Code
          </button>
        </div>
      </header>

      <div className="h-[calc(100vh-4rem)] min-h-0 max-lg:h-[calc(100vh-420px-4rem)]">
        {!hasFiles && (
          <div className="grid h-full place-items-center px-6 text-center text-sm text-[#8f969f]">
            Generated website output will render here after the backend returns files.
          </div>
        )}

        {hasFiles && view === "preview" && (
          <>
            {buildError && (
              <div className="border-b border-[#4a2525] bg-[#261313] px-4 py-3 text-sm text-[#ffd0d0]">
                {buildError}
              </div>
            )}
            <iframe
              key={`${fileNames.join("|")}:${buildStatus}`}
              title="Generated website preview"
              srcDoc={previewHtml}
              sandbox="allow-scripts"
              className="h-full w-full border-0 bg-white"
            />
          </>
        )}

        {hasFiles && view === "code" && (
          <div className="grid h-full grid-cols-[260px_1fr] min-[0px]:min-h-0 max-md:grid-cols-1 max-md:grid-rows-[180px_1fr]">
            <aside className="min-h-0 overflow-y-auto border-r border-[#2a2c31] bg-[#15161a] max-md:border-b max-md:border-r-0">
              {fileNames.map((name) => (
                <button
                  type="button"
                  key={name}
                  onClick={() => setSelectedFile(name)}
                  className={`block w-full border-b border-[#24272d] px-4 py-3 text-left text-sm transition ${
                    selectedFile === name
                      ? "bg-[#d3ff72] text-[#12140f]"
                      : "text-[#d8dce0] hover:bg-[#20232a]"
                  }`}
                >
                  {name}
                </button>
              ))}
            </aside>

            <div className="min-h-0 overflow-hidden bg-[#090a0d]">
              <div className="sticky top-0 border-b border-[#2a2c31] bg-[#111217] px-4 py-3 text-sm text-[#f8f4ea]">
                {selectedFile}
              </div>
              <div className="h-[calc(100%-49px)]">
                <Editor
                  theme="vs-dark"
                  language={languageForFile(selectedFile)}
                  value={files[selectedFile] || ""}
                  onChange={(value: string | undefined) => {
                    if (!selectedFile) return
                    updateFile(selectedFile, value ?? "")
                  }}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 13,
                    smoothScrolling: true,
                    automaticLayout: true,
                    wordWrap: "on",
                  }}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
