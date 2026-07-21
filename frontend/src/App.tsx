import { useState } from "react"
import ChatPanel from "./Components/ChatPanel"
import PreviewPanel from "./Components/PreviewPanel"
import { usePreviewStore } from "./store/previewStore"
import AssetStudio from "./Components/AssetStudio"

export type GeneratedFiles = Record<string, string>

export interface GenerationMeta {
  fileCount: number
  pageCount: number
  lastPrompt: string
  previewUrl: string
}

export interface WireframeSection {
  order: number
  section_name: string
  section_goal: string
  layout: string
  visual_style: string
  animations: string[]
  interactions: string[]
}

export interface WireframePage {
  page_name: string
  page_goal: string
  priority: string
  sections: WireframeSection[]
}

export interface DesignSession {
  session_id: string
  status: "wireframe_ready" | "page_code_review" | "pages_complete" | "asset_selection_ready" | "asset_options_ready" | "completed"
  prompt: string
  selected_style: string
  wireframe: { pages: WireframePage[] }
  asset_options?: {
    assets: Array<{
      asset_id: string
      page_name: string
      section_name: string
      purpose: string
      asset_type: string
      generation_required: boolean
    }>
  }
  generated_assets?: Array<{
    asset_id: string
    asset_type: string
    file_path: string
    preview_url: string
    status: string
    source_asset_id?: string | null
  }>
  selected_asset_ids: string[]
  approved_pages: string[]
}

export default function App() {
  const setFiles = usePreviewStore((state) => state.setFiles)
  const [meta, setMeta] = useState<GenerationMeta>({
    fileCount: 0,
    pageCount: 0,
    lastPrompt: "",
    previewUrl: ""
  })
  const [designSession, setDesignSession] = useState<DesignSession | null>(null)
  const [activeScreen, setActiveScreen] = useState<"design" | "asset-studio">("design")

  const handleGenerated = (nextFiles: GeneratedFiles, prompt: string, previewUrl = "/generated-preview/") => {
    setFiles(nextFiles, prompt)
    setDesignSession(null)
    setMeta({
      fileCount: Object.keys(nextFiles).length,
      pageCount: Object.keys(nextFiles).filter((name) => name.startsWith("src/pages/")).length,
      lastPrompt: prompt,
      previewUrl
    })
  }

  return (
    <main className="h-screen w-screen overflow-hidden bg-[#07080b] text-[#f7f2e8]">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_18%_8%,rgba(211,255,114,0.13),transparent_28rem),radial-gradient(circle_at_82%_18%,rgba(97,157,255,0.14),transparent_30rem),linear-gradient(135deg,#07080b_0%,#101116_48%,#08090d_100%)]" />
      
      <div
        className={`absolute inset-0 ${activeScreen === "design" ? "block" : "hidden"}`}
        aria-hidden={activeScreen !== "design"}
      >
        <div className="grid h-full w-full grid-cols-[minmax(480px,0.95fr)_minmax(420px,1fr)] gap-3 p-3 max-xl:grid-cols-[minmax(430px,0.9fr)_minmax(380px,1fr)] max-lg:grid-cols-1 max-lg:grid-rows-[minmax(520px,58vh)_1fr] max-sm:grid-rows-[minmax(560px,62vh)_1fr] max-sm:gap-2 max-sm:p-2">
          <ChatPanel
            meta={meta}
            designSession={designSession}
            onWireframe={setDesignSession}
          />
          <PreviewPanel
            meta={meta}
            designSession={designSession}
            onDesignSession={setDesignSession}
            onGenerated={handleGenerated}
            onOpenAssetStudio={() => setActiveScreen("asset-studio")}
          />
        </div>
      </div>

      <div
        className={`absolute inset-0 ${activeScreen === "asset-studio" ? "block" : "hidden"}`}
        aria-hidden={activeScreen !== "asset-studio"}
      >
        <AssetStudio
          sessionId={designSession?.session_id}
          prompt={designSession?.prompt}
          onClose={() => setActiveScreen("design")}
          onSession={setDesignSession}
          onGenerated={handleGenerated}
        />
      </div>
    </main>
  )
}
