import { useEffect, useMemo, useRef, useState } from "react"
import Editor from "@monaco-editor/react"

import type { DesignSession, GeneratedFiles, GenerationMeta } from "../App"
import { usePreviewStore } from "../store/previewStore"

interface Props {
  meta: GenerationMeta
  designSession: DesignSession | null
  onDesignSession: (session: DesignSession | null) => void
  onGenerated: (files: GeneratedFiles, prompt: string, previewUrl?: string) => void
  onOpenAssetStudio?: () => void
}

function languageForFile(path: string): string {
  if (path.endsWith(".json")) return "json"
  if (path.endsWith(".css")) return "css"
  if (path.endsWith(".html")) return "html"
  if (path.endsWith(".ts") || path.endsWith(".tsx")) return "typescript"
  return "javascript"
}



function AssetEditControl({
  session,
  assetId,
  onSession,
}: {
  session: DesignSession
  assetId: string
  onSession: (session: DesignSession) => void
}) {
  const [instruction, setInstruction] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")

  const editAsset = async () => {
    if (!instruction.trim()) return
    setBusy(true)
    setError("")
    try {
      const response = await fetch(`/design-sessions/${session.session_id}/edit-asset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ asset_id: assetId, instruction: instruction.trim() }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || "Could not edit this asset")
      onSession(data as DesignSession)
      setInstruction("")
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Could not edit this asset")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mt-3 border-t border-white/10 pt-3" onClick={(event) => event.stopPropagation()}>
      <textarea value={instruction} onChange={(event) => setInstruction(event.target.value)} rows={2} placeholder="Edit this visual in plain language..." className="w-full resize-none rounded border border-white/10 bg-black/20 p-2 text-xs text-[#fffaf0] outline-none placeholder:text-[#737b87]" />
      <button type="button" onClick={editAsset} disabled={busy || !instruction.trim()} className="mt-2 rounded border border-white/15 px-3 py-1.5 text-xs text-[#d3ff72] disabled:opacity-50">
        {busy ? "Updating..." : "Edit this visual"}
      </button>
      {error && <div className="mt-1 text-xs text-red-200">{error}</div>}
    </div>
  )
}

type DeviceMode = "desktop" | "tablet" | "mobile"

function BrowserPreview({
  url,
  title,
  reloadToken = 0,
}: {
  url: string
  title: string
  reloadToken?: number
}) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const unavailableTimerRef = useRef<number | null>(null)
  const [device, setDevice] = useState<DeviceMode>("desktop")
  const [zoom, setZoom] = useState(100)
  const [loading, setLoading] = useState(true)
  const [unavailable, setUnavailable] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [reloadCount, setReloadCount] = useState(0)

  const deviceConfig = {
    desktop: { label: "Desktop", width: "100%", height: "100%", viewport: "Full viewport" },
    tablet: { label: "Tablet", width: 820, height: 1060, viewport: "820 x 1060" },
    mobile: { label: "Mobile", width: 390, height: 844, viewport: "390 x 844" },
  } as const
  const activeDevice = deviceConfig[device]
  const frameKey = `${url}-${reloadToken}-${reloadCount}`

  const reloadPreview = () => {
    setLoading(true)
    setUnavailable(false)
    setReloadCount((value) => value + 1)
  }

  const clearUnavailableTimer = () => {
    if (unavailableTimerRef.current !== null) {
      window.clearTimeout(unavailableTimerRef.current)
      unavailableTimerRef.current = null
    }
  }

  useEffect(() => {
    setLoading(true)
    setUnavailable(false)
    clearUnavailableTimer()
    unavailableTimerRef.current = window.setTimeout(() => {
      unavailableTimerRef.current = null
      setUnavailable(true)
    }, 8000)
    return clearUnavailableTimer
  }, [frameKey])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && isFullscreen) setIsFullscreen(false)
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "r") {
        event.preventDefault()
        reloadPreview()
      }
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [isFullscreen])

  const preview = (
    <div className="relative flex min-h-0 flex-1 overflow-hidden bg-[#0a0b0f]">
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.025)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.025)_1px,transparent_1px)] bg-[size:24px_24px]" />
      <div className="relative flex min-h-0 flex-1 items-center justify-center overflow-auto p-5">
        <div
          className={`origin-center transition-[width,height,transform,border-radius,box-shadow] duration-300 ease-out ${device === "desktop" ? "h-full w-full" : "shrink-0 overflow-hidden rounded-[26px] border-[8px] border-[#252831] shadow-[0_24px_70px_rgba(0,0,0,0.48)]"}`}
          style={{
            width: activeDevice.width,
            height: activeDevice.height,
            transform: `scale(${zoom / 100})`,
          }}
        >
          <iframe
            ref={iframeRef}
            key={frameKey}
            title={title}
            src={url}
            onLoad={() => {
              clearUnavailableTimer()
              setLoading(false)
              setUnavailable(false)
            }}
            onError={() => {
              clearUnavailableTimer()
              setLoading(false)
              setUnavailable(true)
            }}
            className="h-full w-full border-0 bg-white"
          />
        </div>
      </div>

      {loading && !unavailable && (
        <div className="absolute inset-0 grid place-items-center bg-[#0a0b0f]/75 backdrop-blur-sm">
          <div className="text-center">
            <div className="mx-auto mb-3 h-9 w-9 animate-spin rounded-full border-2 border-white/15 border-t-[#d3ff72]" />
            <p className="text-sm font-medium text-[#fffaf0]">Loading preview</p>
            <p className="mt-1 text-xs text-[#7f8792]">Starting the generated website...</p>
          </div>
        </div>
      )}

      {unavailable && (
        <div className="absolute inset-0 grid place-items-center bg-[#0a0b0f] px-6 text-center">
          <div className="max-w-sm">
            <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl border border-white/10 bg-white/[0.04] text-[#d3ff72]">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M4 4h16v12H4z"/><path d="M8 20h8M12 16v4"/><path d="M8 10h.01M12 10h.01M16 10h.01"/></svg>
            </div>
            <h3 className="text-base font-semibold text-[#fffaf0]">Preview server is not running</h3>
            <p className="mt-2 text-sm leading-6 text-[#8f969f]">Start the generated site preview, then retry. The editor will stay open while the preview reconnects.</p>
            <button type="button" onClick={reloadPreview} className="mt-5 rounded-md border border-[#d3ff72]/35 bg-[#d3ff72]/10 px-4 py-2 text-sm font-medium text-[#d3ff72] transition hover:bg-[#d3ff72]/20">Retry preview</button>
          </div>
        </div>
      )}
    </div>
  )

  return (
    <div className={isFullscreen ? "fixed inset-0 z-[100] flex flex-col bg-[#090a0d]" : "flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-white/10 bg-[#101116] shadow-2xl shadow-black/30"}>
      <div className="flex min-h-12 shrink-0 items-center gap-2 border-b border-white/10 bg-[#15171c]/95 px-3 backdrop-blur-xl">
        <div className="flex items-center gap-1.5 px-1">
          <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#ffbd2e]" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
        </div>
        <div className="flex min-w-0 flex-1 items-center gap-2 rounded-lg border border-white/10 bg-black/25 px-3 py-1.5 text-xs text-[#a9b0bb]">
          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[#d3ff72]" />
          <span className="truncate">{url}</span>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button type="button" onClick={reloadPreview} title="Refresh preview (Ctrl/Cmd + R)" className="grid h-8 w-8 place-items-center rounded-md text-[#a9b0bb] transition hover:bg-white/10 hover:text-white">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 11a8.1 8.1 0 0 0-15.5-2M4 5v4h4M4 13a8.1 8.1 0 0 0 15.5 2M20 19v-4h-4"/></svg>
          </button>
          <button type="button" onClick={() => window.open(url, "_blank", "noopener,noreferrer")} title="Open in browser" className="grid h-8 w-8 place-items-center rounded-md text-[#a9b0bb] transition hover:bg-white/10 hover:text-white">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 3h7v7M10 14 21 3M21 14v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h6"/></svg>
          </button>
          <button type="button" onClick={() => setIsFullscreen((value) => !value)} title={isFullscreen ? "Exit fullscreen (Esc)" : "Fullscreen preview"} className="grid h-8 w-8 place-items-center rounded-md text-[#a9b0bb] transition hover:bg-white/10 hover:text-white">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d={isFullscreen ? "M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" : "M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"}/></svg>
          </button>
        </div>
      </div>
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-white/8 bg-[#101116] px-3 py-2">
        <div className="flex rounded-md border border-white/10 bg-black/20 p-0.5">
          {(Object.keys(deviceConfig) as DeviceMode[]).map((mode) => (
            <button key={mode} type="button" onClick={() => setDevice(mode)} className={`rounded px-2.5 py-1 text-xs transition ${device === mode ? "bg-white/10 text-[#fffaf0]" : "text-[#737b87] hover:text-white"}`}>{deviceConfig[mode].label}</button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden text-[11px] text-[#737b87] sm:inline">{activeDevice.viewport}</span>
          <select value={zoom} onChange={(event) => setZoom(Number(event.target.value))} className="rounded-md border border-white/10 bg-black/20 px-2 py-1 text-xs text-[#cbd0d7] outline-none focus:border-[#d3ff72]/50">
            {[50, 75, 100, 125, 150].map((value) => <option key={value} value={value}>{value}%</option>)}
          </select>
        </div>
      </div>
      {preview}
    </div>
  )
}

function ImageXBox({ className }: { className?: string }) {
  return (
    <div className={`relative overflow-hidden border-2 border-[#d1d5db] bg-[#f3f4f6] ${className || ""}`}>
      <svg className="absolute inset-0 h-full w-full stroke-[#d1d5db]" strokeWidth="2" preserveAspectRatio="none">
        <line x1="0" y1="0" x2="100%" y2="100%" />
        <line x1="100%" y1="0" x2="0" y2="100%" />
      </svg>
    </div>
  )
}

function FullWireframeBlock({ layout, title }: { layout: string; title: string }) {
  const normalized = layout.toLowerCase();
  
  if (normalized.includes("split") || normalized.includes("two")) {
    return (
      <div className="flex w-full flex-col md:flex-row gap-8 p-8 bg-white">
        <div className="flex flex-1 flex-col justify-center gap-4">
          <div className="h-6 w-3/4 bg-[#9ca3af]" />
          <div className="h-3 w-full bg-[#e5e7eb]" />
          <div className="h-3 w-full bg-[#e5e7eb]" />
          <div className="h-3 w-5/6 bg-[#e5e7eb]" />
          <div className="mt-4 h-8 w-32 border-2 border-[#9ca3af] bg-transparent" />
        </div>
        <div className="flex-1">
          <ImageXBox className="aspect-video w-full" />
        </div>
      </div>
    );
  }
  
  if (normalized.includes("grid") || normalized.includes("card")) {
    return (
      <div className="flex w-full flex-col items-center gap-8 p-8 bg-white">
        <div className="h-8 w-1/3 bg-[#9ca3af] uppercase tracking-widest text-center flex items-center justify-center font-bold text-white text-xs px-2 truncate">{title}</div>
        <div className="grid w-full grid-cols-1 md:grid-cols-3 gap-6">
          <div className="flex flex-col gap-3">
            <ImageXBox className="aspect-video w-full" />
            <div className="h-2 w-full bg-[#e5e7eb]" />
            <div className="h-2 w-2/3 bg-[#e5e7eb]" />
          </div>
          <div className="flex flex-col gap-3">
            <ImageXBox className="aspect-video w-full" />
            <div className="h-2 w-full bg-[#e5e7eb]" />
            <div className="h-2 w-2/3 bg-[#e5e7eb]" />
          </div>
          <div className="flex flex-col gap-3">
            <ImageXBox className="aspect-video w-full" />
            <div className="h-2 w-full bg-[#e5e7eb]" />
            <div className="h-2 w-2/3 bg-[#e5e7eb]" />
          </div>
        </div>
      </div>
    );
  }
  
  if (normalized.includes("full")) {
    return (
      <div className="relative flex min-h-[400px] w-full items-center justify-center bg-[#f3f4f6] p-8 border-b-2 border-[#d1d5db] overflow-hidden">
        <div className="absolute inset-0">
          <svg className="absolute inset-0 h-full w-full stroke-[#e5e7eb]" strokeWidth="2" preserveAspectRatio="none">
            <line x1="0" y1="0" x2="100%" y2="100%" />
            <line x1="100%" y1="0" x2="0" y2="100%" />
          </svg>
        </div>
        <div className="relative z-10 flex w-full max-w-2xl flex-col items-center gap-6 bg-white/90 p-10 text-center border-2 border-[#d1d5db]">
          <div className="h-10 w-3/4 bg-[#6b7280] flex items-center justify-center font-black text-white uppercase tracking-widest text-xl truncate px-4">{title}</div>
          <div className="flex w-full flex-col items-center gap-3">
            <div className="h-3 w-full bg-[#e5e7eb]" />
            <div className="h-3 w-5/6 bg-[#e5e7eb]" />
          </div>
          <div className="h-10 w-40 border-2 border-[#6b7280] bg-transparent flex items-center justify-center text-[#6b7280] font-bold text-sm">GET STARTED</div>
        </div>
      </div>
    );
  }
  
  // Default: Simple stacked
  return (
    <div className="flex w-full flex-col items-center gap-6 p-12 bg-white">
      <div className="h-6 w-1/2 bg-[#9ca3af] flex items-center justify-center font-bold text-white uppercase text-sm truncate px-4">{title}</div>
      <div className="h-3 w-3/4 bg-[#e5e7eb]" />
      <div className="h-3 w-2/3 bg-[#e5e7eb]" />
      <div className="h-3 w-3/4 bg-[#e5e7eb]" />
      <ImageXBox className="mt-4 aspect-video w-full max-w-3xl" />
    </div>
  );
}

function WireframeReview({
  session,
  onSession,
  onGenerated,
  onOpenAssetStudio,
}: {
  session: DesignSession
  onSession: (session: DesignSession) => void
  onGenerated: (files: GeneratedFiles, prompt: string, previewUrl?: string) => void
  onOpenAssetStudio?: () => void
}) {
  const [selectedAssetIds, setSelectedAssetIds] = useState<string[]>(session.selected_asset_ids)
  const [selectedSection, setSelectedSection] = useState<{ pageName: string; order: number } | null>(null)
  const [editInstruction, setEditInstruction] = useState("")
  const [showAddPage, setShowAddPage] = useState(false)
  const [pagePrompt, setPagePrompt] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSelectedAssetIds(session.selected_asset_ids)
  }, [session.session_id, session.selected_asset_ids])

  const approve = async () => {
    setBusy(true)
    setError("")
    try {
      const response = await fetch(`/design-sessions/${session.session_id}/approve`, { method: "POST" })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || "Could not plan assets")
      onSession(data as DesignSession)
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Could not plan assets")
    } finally {
      setBusy(false)
    }
  }

  const generateOptions = async () => {
    setBusy(true)
    setError("")
    try {
      const response = await fetch(`/design-sessions/${session.session_id}/generate-assets`, { method: "POST" })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || "Could not generate asset options")
      onSession(data as DesignSession)
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Could not generate asset options")
    } finally {
      setBusy(false)
    }
  }

  const generate = async () => {
    setBusy(true)
    setError("")
    try {
      const response = await fetch(`/design-sessions/${session.session_id}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ asset_ids: selectedAssetIds }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || "Could not generate the site")
      onSession(data.session as DesignSession)
      const result = data.result || {}
      onGenerated(result.files || {}, session.prompt, result.preview_url || "/generated-preview/")
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Could not generate the site")
    } finally {
      setBusy(false)
    }
  }

  const toggleAsset = (assetId: string) => {
    setSelectedAssetIds((current) => current.includes(assetId)
      ? current.filter((id) => id !== assetId)
      : [...current, assetId])
  }

  const editSection = async () => {
    if (!selectedSection || !editInstruction.trim()) return
    setBusy(true)
    setError("")
    try {
      const response = await fetch(`/design-sessions/${session.session_id}/edit-section`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          page_name: selectedSection.pageName,
          section_order: selectedSection.order,
          instruction: editInstruction.trim(),
        }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || "Could not edit this section")
      onSession(data as DesignSession)
      setEditInstruction("")
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Could not edit this section")
    } finally {
      setBusy(false)
    }
  }

  const addPage = async () => {
    if (!pagePrompt.trim()) return
    setBusy(true)
    setError("")
    try {
      const response = await fetch(`/design-sessions/${session.session_id}/pages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: pagePrompt.trim() }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || "Could not add page")
      onSession(data as DesignSession)
      setPagePrompt("")
      setShowAddPage(false)
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Could not add page")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="h-full overflow-y-auto bg-[#0b0c10] p-4">
      <div className="mx-auto max-w-5xl space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-4 rounded-lg border border-[#d3ff72]/25 bg-[#d3ff72]/[0.06] p-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[#d3ff72]">Wireframe review</div>
            <h2 className="mt-2 text-xl font-semibold text-[#fffaf0]">Review structure before assets or code</h2>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setShowAddPage(true)}
              className="rounded-lg border border-[#d3ff72]/30 bg-[#d3ff72]/10 px-3 py-2 text-sm font-medium text-[#d3ff72] transition hover:bg-[#d3ff72]/20"
            >
              + Add page
            </button>
            {onOpenAssetStudio && (
              <button
                type="button"
                onClick={onOpenAssetStudio}
                className="rounded-lg border border-[#d3ff72]/30 bg-[#d3ff72]/10 px-3 py-2 text-sm font-medium text-[#d3ff72] transition hover:bg-[#d3ff72]/20"
              >
                Asset Studio
              </button>
            )}
            <div className="flex shrink-0 rounded-lg border border-white/10 bg-black/20 p-1">
              <button type="button" className="rounded-md bg-[#d3ff72] px-4 py-2 text-sm font-medium text-[#12140f]">
                Preview
              </button>
              <button type="button" disabled className="rounded-md px-4 py-2 text-sm font-medium text-[#6f7783] opacity-60">
                Code
              </button>
            </div>
            {session.status === "wireframe_ready" && (
              <button type="button" onClick={approve} disabled={busy} className="rounded-md bg-[#d3ff72] px-4 py-2 text-sm font-semibold text-[#12140f] disabled:opacity-50">
                {busy ? "Generating project shell..." : "Approve & generate code"}
              </button>
            )}
          </div>
          {showAddPage && (
            <div className="basis-full rounded-md border border-white/10 bg-black/20 p-3">
              <div className="text-xs font-semibold text-[#fffaf0]">New page prompt</div>
              <textarea value={pagePrompt} onChange={(event) => setPagePrompt(event.target.value)} rows={3} placeholder="Describe the next page..." className="mt-2 w-full resize-none rounded border border-white/10 bg-black/20 p-2 text-sm text-white outline-none placeholder:text-[#737b87]" />
              <div className="mt-2 flex gap-2">
                <button type="button" onClick={addPage} disabled={busy || !pagePrompt.trim()} className="rounded bg-[#d3ff72] px-3 py-1.5 text-xs font-semibold text-[#12140f] disabled:opacity-50">{busy ? "Adding..." : "Add page"}</button>
                <button type="button" onClick={() => setShowAddPage(false)} className="rounded border border-white/10 px-3 py-1.5 text-xs text-[#a9b0bb]">Cancel</button>
              </div>
            </div>
          )}
          {session.status === "asset_selection_ready" && (
            <button type="button" onClick={generateOptions} disabled={busy} className="rounded-md bg-[#d3ff72] px-4 py-2 text-sm font-semibold text-[#12140f] disabled:opacity-50">
              {busy ? "Creating options..." : "Create asset options"}
            </button>
          )}
          {session.status === "asset_options_ready" && (
            <button type="button" onClick={generate} disabled={busy} className="rounded-md bg-[#d3ff72] px-4 py-2 text-sm font-semibold text-[#12140f] disabled:opacity-50">
              {busy ? "Generating..." : "Generate final React site"}
            </button>
          )}
        </div>

        {session.wireframe.pages.map((page) => (
          <article key={page.page_name} className="overflow-hidden rounded-lg border border-white/10 bg-[#15161a]">
            <header className="border-b border-white/10 bg-white/[0.03] px-5 py-4">
              <div className="text-xs uppercase tracking-[0.16em] text-[#7f8792]">{page.priority} priority page</div>
              <h3 className="mt-1 text-lg font-semibold text-[#fffaf0]">{page.page_name}</h3>
              <p className="mt-1 text-sm text-[#a9b0bb]">{page.page_goal}</p>
            </header>
            <div className="flex justify-center bg-[#f3f4f6] p-8 rounded-b-lg">
              <div className="flex w-full max-w-4xl flex-col overflow-hidden border-2 border-[#d1d5db] bg-white shadow-2xl">
                {page.sections.map((section) => (
                  <button
                    type="button"
                    key={`${page.page_name}-${section.order}-${section.section_name}`}
                    onClick={() => setSelectedSection({ pageName: page.page_name, order: section.order })}
                    className={`group relative w-full border-b-2 border-[#d1d5db] last:border-b-0 text-left transition-all ${
                      selectedSection?.pageName === page.page_name && selectedSection.order === section.order
                        ? "z-10 ring-8 ring-inset ring-[#d3ff72]"
                        : "z-0 hover:ring-4 hover:ring-inset hover:ring-[#d3ff72]/50"
                    }`}
                  >
                    <FullWireframeBlock layout={section.layout} title={section.section_name} />
                  </button>
                ))}
              </div>
            </div>
          </article>
        ))}

        {session.status === "wireframe_ready" && selectedSection && (
          <section className="rounded-lg border border-white/10 bg-[#15161a] p-5">
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[#d3ff72]">Edit selected section</div>
            <p className="mt-1 text-sm text-[#a9b0bb]">The agent receives only this selected wireframe section. Other pages and sections remain unchanged.</p>
            <textarea value={editInstruction} onChange={(event) => setEditInstruction(event.target.value)} rows={3} placeholder="Example: Make this a compact two-column section with no media and subtle CSS reveal motion." className="mt-3 w-full resize-none rounded-md border border-white/10 bg-black/20 p-3 text-sm text-[#fffaf0] outline-none placeholder:text-[#737b87] focus:border-[#d3ff72]/60" />
            <button type="button" onClick={editSection} disabled={busy || !editInstruction.trim()} className="mt-3 rounded-md border border-[#d3ff72]/40 px-4 py-2 text-sm font-medium text-[#d3ff72] hover:bg-[#d3ff72]/10 disabled:opacity-50">
              {busy ? "Editing..." : "Apply section edit"}
            </button>
          </section>
        )}

        {session.status === "asset_selection_ready" && (
          <section className="rounded-lg border border-white/10 bg-[#15161a] p-5">
            <h3 className="text-lg font-semibold text-[#fffaf0]">Preparing visual options</h3>
            <p className="mt-1 text-sm text-[#a9b0bb]">The approved design needs these visual slots. Generate the options to review the actual images and videos.</p>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {(session.asset_options?.assets || []).map((asset) => (
                <div key={asset.asset_id} className="rounded-md border border-white/10 bg-black/15 p-4">
                  <span className="block font-medium text-[#fffaf0]">{asset.section_name}</span>
                  <span className="mt-1 block text-sm text-[#a9b0bb]">{asset.asset_type}: {asset.purpose}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {session.status === "asset_options_ready" && (
          <section className="rounded-lg border border-white/10 bg-[#15161a] p-5">
            <h3 className="text-lg font-semibold text-[#fffaf0]">Choose your visual assets</h3>
            <p className="mt-1 text-sm text-[#a9b0bb]">Select an image or video for each planned visual. Leave it unselected to use color and CSS motion.</p>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {(session.generated_assets || []).filter((asset) => !asset.asset_id.endsWith("_source")).map((asset) => (
                <label key={asset.asset_id} className="cursor-pointer rounded-md border border-white/10 bg-black/15 p-3 hover:border-[#d3ff72]/60">
                  <div className="mb-3 aspect-video overflow-hidden rounded bg-black/30">
                    {asset.asset_type === "video" ? (
                      <video src={asset.preview_url} controls muted className="h-full w-full object-cover" />
                    ) : (
                      <img src={asset.preview_url} alt="Generated asset option" className="h-full w-full object-cover" />
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-sm text-[#fffaf0]">
                    <input type="checkbox" checked={selectedAssetIds.includes(asset.asset_id)} onChange={() => toggleAsset(asset.asset_id)} className="h-4 w-4 accent-[#d3ff72]" />
                    Use this {asset.asset_type}
                  </div>
                  <AssetEditControl session={session} assetId={asset.asset_id} onSession={onSession} />
                </label>
              ))}
            </div>
          </section>
        )}
        {error && <div className="rounded-md border border-red-400/40 bg-red-500/10 p-3 text-sm text-red-100">{error}</div>}
      </div>
    </div>
  )
}

function PageCodeReview({
  session,
  onSession,
  onGenerated,
  onOpenAssetStudio,
}: {
  session: DesignSession
  onSession: (session: DesignSession) => void
  onGenerated: (files: GeneratedFiles, prompt: string, previewUrl?: string) => void
  onOpenAssetStudio?: () => void
}) {
  const pages = session.wireframe.pages
  const approvedPages: string[] = session.approved_pages ?? []
  const [activePage, setActivePage] = useState<string>(pages[0]?.page_name ?? "")
  const [editInstruction, setEditInstruction] = useState("")
  const [generatingPage, setGeneratingPage] = useState<string | null>(null)
  const [pagePreviewUrls, setPagePreviewUrls] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [iframeKey, setIframeKey] = useState(0)
  const [showAddPage, setShowAddPage] = useState(false)
  const [pagePrompt, setPagePrompt] = useState("")



  const skipAssets = async () => {
    setBusy(true)
    setError("")
    try {
      const response = await fetch(`/design-sessions/${session.session_id}/skip-assets`, { method: "POST" })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || "Could not skip assets")
      onSession(data.session as DesignSession)
      const result = data.result || {}
      onGenerated(result.files || {}, session.prompt, result.preview_url || "/generated-preview/")
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Could not skip assets")
    } finally {
      setBusy(false)
    }
  }

  const generatePageCode = async (pageName: string, instruction?: string) => {
    setGeneratingPage(pageName)
    setError("")
    try {
      const response = await fetch(`/design-sessions/${session.session_id}/generate-page-code`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ page_name: pageName, instruction: instruction || null }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || "Could not generate page code")
      if (data.session) onSession(data.session as DesignSession)
      const pageIndex = pages.findIndex((p) => p.page_name === pageName)
      const routePath = pageIndex === 0 ? "/" : "/" + pageName.toLowerCase().replace(/[^a-z0-9]+/g, "-")
      const previewUrl = `http://localhost:5174${routePath}`
      setPagePreviewUrls((prev) => ({ ...prev, [pageName]: previewUrl }))
      setIframeKey((k) => k + 1)
      setEditInstruction("")
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Could not generate page code")
    } finally {
      setGeneratingPage(null)
    }
  }

  const approvePage = async (pageName: string) => {
    setBusy(true)
    setError("")
    try {
      const response = await fetch(`/design-sessions/${session.session_id}/approve-page`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ page_name: pageName }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || "Could not approve page")
      onSession(data as DesignSession)
      const next = pages.find((p) => !data.approved_pages.includes(p.page_name))
      if (next) setActivePage(next.page_name)
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Could not approve page")
    } finally {
      setBusy(false)
    }
  }

  const addPage = async () => {
    if (!pagePrompt.trim()) return
    setBusy(true)
    setError("")
    try {
      const response = await fetch(`/design-sessions/${session.session_id}/pages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: pagePrompt.trim() }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || "Could not add page")
      onSession(data as DesignSession)
      const added = data.wireframe.pages[data.wireframe.pages.length - 1]
      setActivePage(added.page_name)
      setPagePrompt("")
      setShowAddPage(false)
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Could not add page")
    } finally {
      setBusy(false)
    }
  }

  const previewUrl = pagePreviewUrls[activePage]

  return (
    <div className="flex h-full flex-col overflow-hidden bg-[#0b0c10]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-5 py-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[#d3ff72]">Page Code Review</div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={() => setShowAddPage(true)}
            className="rounded-lg border border-[#d3ff72]/30 bg-[#d3ff72]/10 px-3 py-2 text-sm font-medium text-[#d3ff72] transition hover:bg-[#d3ff72]/20"
          >
            + Add page
          </button>
          {onOpenAssetStudio && (
            <button
              type="button"
              onClick={onOpenAssetStudio}
              className="rounded-lg border border-[#d3ff72]/30 bg-[#d3ff72]/10 px-3 py-2 text-sm font-medium text-[#d3ff72] transition hover:bg-[#d3ff72]/20"
            >
              Asset Studio
            </button>
          )}
          <div className="flex shrink-0 rounded-lg border border-white/10 bg-black/20 p-1">
            <button
              type="button"
              className="rounded-md bg-[#d3ff72] px-4 py-2 text-sm font-medium text-[#12140f]"
            >
              Preview
            </button>
            <button
              type="button"
              disabled
              title="Code view is available in the final generated workspace."
              className="rounded-md px-4 py-2 text-sm font-medium text-[#6f7783] opacity-60"
            >
              Code
            </button>
          </div>
          {session.status === "pages_complete" && (
            <button type="button" onClick={skipAssets} disabled={busy} className="ml-2 rounded-md border border-white/20 bg-white/10 px-4 py-2 text-sm font-semibold text-white hover:bg-white/20 disabled:opacity-50">
              {busy ? "Skipping..." : "Skip Assets"}
            </button>
          )}
        </div>
      </div>

      <div className="flex min-h-0 flex-1">
        <aside className="flex w-52 shrink-0 flex-col border-r border-white/10 bg-[#0e0f13]">
          <div className="flex items-center justify-between px-4 pt-4 pb-2">
            <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#5b6470]">Pages</div>
            <button type="button" onClick={() => setShowAddPage(true)} className="grid h-7 w-7 place-items-center rounded border border-[#d3ff72]/30 text-lg text-[#d3ff72] hover:bg-[#d3ff72]/10" title="Add page">+</button>
          </div>
          {pages.map((page) => {
            const isApproved = approvedPages.includes(page.page_name)
            const hasPreview = Boolean(pagePreviewUrls[page.page_name])
            const isActive = activePage === page.page_name
            return (
              <button
                key={page.page_name}
                type="button"
                onClick={() => setActivePage(page.page_name)}
                className={`flex items-center gap-2 border-b border-white/8 px-4 py-3 text-left text-sm transition ${
                  isActive ? "bg-[#d3ff72]/10 text-[#d3ff72]" : "text-[#c2c7ce] hover:bg-white/5"
                }`}
              >
                <span className={`h-2 w-2 shrink-0 rounded-full ${
                  isApproved ? "bg-[#d3ff72]" : hasPreview ? "bg-yellow-400" : "bg-[#3a3f4a]"
                }`} />
                <span className="truncate">{page.page_name}</span>
              </button>
            )
          })}
          {showAddPage && (
            <div className="m-3 rounded-md border border-white/10 bg-white/[0.04] p-3">
              <div className="text-xs font-semibold text-[#fffaf0]">New page prompt</div>
              <textarea value={pagePrompt} onChange={(event) => setPagePrompt(event.target.value)} rows={4} placeholder="Describe the next page..." className="mt-2 w-full resize-none rounded border border-white/10 bg-black/20 p-2 text-xs text-white outline-none placeholder:text-[#737b87]" />
              <div className="mt-2 flex gap-2">
                <button type="button" onClick={addPage} disabled={busy || !pagePrompt.trim()} className="flex-1 rounded bg-[#d3ff72] px-2 py-1.5 text-xs font-semibold text-[#12140f] disabled:opacity-50">{busy ? "Adding..." : "Add"}</button>
                <button type="button" onClick={() => setShowAddPage(false)} className="rounded border border-white/10 px-2 py-1.5 text-xs text-[#a9b0bb]">Cancel</button>
              </div>
            </div>
          )}
        </aside>

        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <div className="flex flex-wrap items-center gap-3 border-b border-white/10 bg-[#11121a] px-4 py-3">
            <button
              type="button"
              onClick={() => generatePageCode(activePage)}
              disabled={generatingPage !== null}
              className="rounded-md bg-white/10 px-4 py-2 text-sm font-medium text-[#fffaf0] hover:bg-white/15 disabled:opacity-50"
            >
              {generatingPage === activePage ? "Generating..." : pagePreviewUrls[activePage] ? "Regenerate page" : "Generate page code"}
            </button>
            {pagePreviewUrls[activePage] && !approvedPages.includes(activePage) && (
              <button
                type="button"
                onClick={() => approvePage(activePage)}
                disabled={busy || generatingPage !== null}
                className="rounded-md bg-[#d3ff72] px-4 py-2 text-sm font-semibold text-[#12140f] disabled:opacity-50"
              >
                {busy ? "Approving..." : `Approve "${activePage}"`}
              </button>
            )}
            {approvedPages.includes(activePage) && (
              <span className="rounded-full border border-[#d3ff72]/40 px-3 py-1 text-xs font-semibold text-[#d3ff72]">✓ Approved</span>
            )}
            <div className="ml-auto text-xs text-[#5b6470]">
              {approvedPages.length}/{pages.length} pages approved
            </div>
          </div>

          <div className="relative min-h-0 flex-1 bg-[#08090c]">
            {!previewUrl && generatingPage !== activePage && (
              <div className="grid h-full place-items-center text-center">
                <div className="max-w-xs">
                  <div className="mx-auto mb-4 text-4xl">🖼️</div>
                  <p className="text-sm text-[#a9b0bb]">Click <strong className="text-[#fffaf0]">Generate page code</strong> to build a live preview for <strong className="text-[#fffaf0]">{activePage}</strong>.</p>
                </div>
              </div>
            )}
            {generatingPage === activePage && (
              <div className="grid h-full place-items-center text-center">
                <div className="max-w-xs">
                  <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-[#d3ff72]/30 border-t-[#d3ff72]" />
                  <p className="mt-4 text-sm text-[#a9b0bb]">Generating <strong className="text-[#fffaf0]">{activePage}</strong>…</p>
                </div>
              </div>
            )}
            {previewUrl && generatingPage !== activePage && (
              <BrowserPreview
                url={previewUrl}
                title={`Preview of ${activePage}`}
                reloadToken={iframeKey}
              />
            )}
          </div>

          {pagePreviewUrls[activePage] && (
            <div className="shrink-0 border-t border-white/10 bg-[#11121a] px-4 py-3">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={editInstruction}
                  onChange={(e) => setEditInstruction(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && editInstruction.trim() ? generatePageCode(activePage, editInstruction) : undefined}
                  placeholder={`Edit "${activePage}"… e.g. "Make the hero full-screen with a parallax background"`}
                  className="flex-1 rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm text-[#fffaf0] outline-none placeholder:text-[#5b6470] focus:border-[#d3ff72]/50"
                />
                <button
                  type="button"
                  onClick={() => editInstruction.trim() ? generatePageCode(activePage, editInstruction) : undefined}
                  disabled={!editInstruction.trim() || generatingPage !== null}
                  className="rounded-md border border-[#d3ff72]/40 px-4 py-2 text-sm font-medium text-[#d3ff72] hover:bg-[#d3ff72]/10 disabled:opacity-40"
                >
                  {generatingPage === activePage ? "..." : "Apply"}
                </button>
              </div>
            </div>
          )}
          {error && <div className="shrink-0 border-t border-red-400/20 bg-red-500/10 px-4 py-2 text-sm text-red-200">{error}</div>}
        </div>
      </div>
    </div>
  )
}

export default function PreviewPanel({ meta, designSession, onDesignSession, onGenerated, onOpenAssetStudio }: Props) {
  const {
    files,
    selectedFile,
    view,
    setSelectedFile,
    setView,
    updateFile,
  } = usePreviewStore((state) => state)

  const fileNames = useMemo(() => Object.keys(files), [files])
  const hasFiles = fileNames.length > 0
  const previewUrl = useMemo(() => {
    if (!hasFiles) {
      return ""
    }
    return meta.previewUrl || `/generated-preview/?files=${meta.fileCount}`
  }, [hasFiles, meta.fileCount, meta.previewUrl])

  if (designSession?.status === "page_code_review" || designSession?.status === "pages_complete" || (designSession?.status === "asset_selection_ready" && (designSession.approved_pages?.length ?? 0) > 0)) {
    return (
      <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-xl border border-white/10 bg-[#101116]/88 shadow-2xl shadow-black/40 backdrop-blur-xl">
        <PageCodeReview
          session={designSession!}
          onSession={onDesignSession}
          onGenerated={onGenerated}
          onOpenAssetStudio={onOpenAssetStudio}
        />
      </section>
    )
  }

  if (designSession) {
    return (
      <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-xl border border-white/10 bg-[#101116]/88 shadow-2xl shadow-black/40 backdrop-blur-xl">
        <WireframeReview
          session={designSession}
          onSession={onDesignSession}
          onGenerated={onGenerated}
          onOpenAssetStudio={onOpenAssetStudio}
        />
      </section>
    )
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-xl border border-white/10 bg-[#101116]/88 shadow-2xl shadow-black/40 backdrop-blur-xl">
      <header className="flex min-h-20 items-center justify-between gap-4 border-b border-white/10 px-5 py-4 max-sm:flex-col max-sm:items-start">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-[#737b87]">
            <span className={`h-2 w-2 rounded-full ${hasFiles ? "bg-[#d3ff72]" : "bg-[#5b6470]"}`} />
            {hasFiles ? "Generated workspace" : "Waiting for generation"}
          </div>
          <div className="mt-2 truncate text-sm text-[#9ba3af]">{meta.lastPrompt || "No generation yet"}</div>
          <div className="mt-1 flex flex-wrap items-center gap-3 text-sm font-medium text-[#f8f4ea]">
            <span>{hasFiles ? `${meta.fileCount} files ready` : "Preview waiting for generated files"}</span>
            <span className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-xs text-[#aeb6c2]">
              {hasFiles ? "Preview ready" : "Idle"}
            </span>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            disabled
            title="Create a wireframe before adding more pages."
            className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm font-medium text-[#6f7783] opacity-70"
          >
            + Add page
          </button>
          {onOpenAssetStudio && (
            <button
              type="button"
              onClick={onOpenAssetStudio}
              className="flex items-center gap-1.5 rounded-lg border border-[#d3ff72]/30 bg-[#d3ff72]/10 px-3 py-2 text-sm font-medium text-[#d3ff72] transition hover:bg-[#d3ff72]/20"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>
              </svg>
              Asset Studio
            </button>
          )}
          <div className="flex shrink-0 rounded-lg border border-white/10 bg-black/20 p-1">
            <button
              type="button"
              onClick={() => setView("preview")}
              className={`rounded-md px-4 py-2 text-sm font-medium transition ${
                view === "preview" ? "bg-[#d3ff72] text-[#12140f]" : "text-[#c2c7ce] hover:bg-white/[0.05]"
              }`}
            >
              Preview
            </button>
            <button
              type="button"
              onClick={() => setView("code")}
              className={`rounded-md px-4 py-2 text-sm font-medium transition ${
                view === "code" ? "bg-[#d3ff72] text-[#12140f]" : "text-[#c2c7ce] hover:bg-white/[0.05]"
              }`}
            >
              Code
            </button>
          </div>
        </div>
      </header>

      <div className="min-h-0 flex-1 bg-[#08090c] p-3 max-sm:p-2">
        {!hasFiles && (
          <div className="grid h-full place-items-center rounded-lg border border-dashed border-white/12 bg-[radial-gradient(circle_at_50%_25%,rgba(211,255,114,0.07),transparent_24rem),#0b0c10] px-6 text-center">
            <div className="max-w-sm">
              <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-full border border-white/10 bg-white/[0.04] text-lg text-[#d3ff72]">
                <span className="block h-2.5 w-2.5 rounded-full bg-[#d3ff72]" />
              </div>
              <h2 className="text-lg font-semibold text-[#fffaf0]">Preview is waiting</h2>
              <p className="mt-2 text-sm leading-6 text-[#8f969f]">
                Generated website output will render here after the backend returns files and builds the preview.
              </p>
            </div>
          </div>
        )}

        {hasFiles && view === "preview" && (
          <BrowserPreview url={previewUrl} title="Generated website preview" />
        )}

        {hasFiles && view === "code" && (
          <div className="grid h-full grid-cols-[260px_1fr] overflow-hidden rounded-lg border border-white/10 bg-[#0d0e12] min-[0px]:min-h-0 max-md:grid-cols-1 max-md:grid-rows-[180px_1fr]">
            <aside className="min-h-0 overflow-y-auto border-r border-white/10 bg-[#15161a] max-md:border-b max-md:border-r-0">
              {fileNames.map((name) => (
                <button
                  type="button"
                  key={name}
                  onClick={() => setSelectedFile(name)}
                  className={`block w-full border-b border-white/8 px-4 py-3 text-left text-sm transition ${
                    selectedFile === name
                      ? "bg-[#d3ff72] text-[#12140f]"
                      : "text-[#d8dce0] hover:bg-white/[0.05]"
                  }`}
                >
                  {name}
                </button>
              ))}
            </aside>

            <div className="min-h-0 overflow-hidden bg-[#090a0d]">
              <div className="sticky top-0 flex items-center justify-between gap-3 border-b border-white/10 bg-[#111217] px-4 py-3 text-sm text-[#f8f4ea]">
                <span className="truncate">{selectedFile}</span>
                <span className="rounded-full border border-white/10 px-2 py-0.5 text-xs text-[#9ba3af]">
                  {languageForFile(selectedFile)}
                </span>
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
