import { useState } from "react"
import ChatPanel from "./Components/ChatPanel"
import PreviewPanel from "./Components/PreviewPanel"
import { usePreviewStore } from "./store/previewStore"

export type GeneratedFiles = Record<string, string>

export interface GenerationMeta {
  fileCount: number
  pageCount: number
  lastPrompt: string
}

export default function App() {
  const setFiles = usePreviewStore((state) => state.setFiles)
  const [meta, setMeta] = useState<GenerationMeta>({
    fileCount: 0,
    pageCount: 0,
    lastPrompt: ""
  })

  const handleGenerated = (nextFiles: GeneratedFiles, prompt: string) => {
    setFiles(nextFiles, prompt)
    setMeta({
      fileCount: Object.keys(nextFiles).length,
      pageCount: Object.keys(nextFiles).filter((name) => name.startsWith("src/pages/")).length,
      lastPrompt: prompt
    })
  }

  return (
    <main className="grid h-screen w-screen grid-cols-[360px_1fr] overflow-hidden bg-[#101114] text-[#f4f0e8] max-lg:grid-cols-1 max-lg:grid-rows-[420px_1fr]">
      <ChatPanel onGenerated={handleGenerated} meta={meta} />
      <PreviewPanel meta={meta} />
    </main>
  )
}
