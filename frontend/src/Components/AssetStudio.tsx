import { useEffect, useState, useRef } from "react"
import type { DesignSession, GeneratedFiles } from "../App"

export interface AssetPlan {
  asset_id: string
  page_name: string
  section_name: string
  /** The existing page placeholder this file should replace. */
  target_asset_id?: string
  prompt: string
  width: number
  height: number
  url?: string
  is_parallax?: boolean
  is_video?: boolean
}

/** Shape returned by GET /design-sessions/{id}/pages/placements */
export interface PagePlacement {
  page_name: string
  sections: { asset_id: string; section_name: string }[]
}

type PlacementOption = Pick<AssetPlan, "asset_id" | "page_name" | "section_name">

interface Props {
  sessionId?: string
  prompt?: string
  onClose: () => void
  onSession?: (session: DesignSession) => void
  onGenerated?: (files: GeneratedFiles, prompt: string, previewUrl?: string) => void
}

function AddAssetModal({
  placements,
  livePlacements,
  onAdd,
  onClose,
}: {
  placements: PlacementOption[]
  livePlacements: PagePlacement[]
  onAdd: (a: AssetPlan) => void
  onClose: () => void
}) {
  // Prefer live placements from pages/placements endpoint; fall back to scanned asset list
  const effectivePlacements: PlacementOption[] = livePlacements.length > 0
    ? livePlacements.flatMap((p) =>
        p.sections.map((s) => ({ asset_id: s.asset_id, page_name: p.page_name, section_name: s.section_name }))
      )
    : placements
  const [form, setForm] = useState({ asset_id: "", prompt: "", target_asset_id: "", width: "1920", height: "1080" })
  const selectedPlacement = effectivePlacements.find((placement) => placement.asset_id === form.target_asset_id)
  const pageNames = [...new Set(effectivePlacements.map((placement) => placement.page_name))]
  const [selectedPage, setSelectedPage] = useState("")
  const sectionsForPage = effectivePlacements.filter((placement) => !selectedPage || placement.page_name === selectedPage)

  const submit = () => {
    if (!form.asset_id.trim() || !form.prompt.trim()) return
    onAdd({
      asset_id: form.asset_id.trim().replace(/\s+/g, "_"),
      target_asset_id: selectedPlacement?.asset_id,
      page_name: selectedPlacement?.page_name || "custom",
      section_name: selectedPlacement?.section_name || "custom",
      prompt: form.prompt.trim(),
      width: parseInt(form.width) || 1920,
      height: parseInt(form.height) || 1080,
      is_parallax: false,
    })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-xl border border-white/10 bg-[#0f1015] p-6 shadow-2xl">
        <h3 className="mb-4 text-base font-semibold text-[#fffaf0]">Add New Asset</h3>
        <div className="space-y-3">
          {effectivePlacements.length > 0 ? (
            <>
              <div>
                <label className="mb-1 block text-xs text-[#6b7280]">Target Page</label>
                <select
                  value={selectedPage}
                  onChange={(e) => {
                    setSelectedPage(e.target.value)
                    setForm((current) => ({ ...current, target_asset_id: "" }))
                  }}
                  className="w-full rounded-md border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-[#d3ff72]/50"
                >
                  <option value="">Choose a page</option>
                  {pageNames.map((pageName) => <option key={pageName} value={pageName}>{pageName}</option>)}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs text-[#6b7280]">Target Section</label>
                <select
                  value={form.target_asset_id}
                  onChange={(e) => setForm((current) => ({ ...current, target_asset_id: e.target.value }))}
                  disabled={!selectedPage}
                  className="w-full rounded-md border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-[#d3ff72]/50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <option value="">Choose a section</option>
                  {sectionsForPage.map((placement) => (
                    <option key={placement.asset_id} value={placement.asset_id}>
                      {placement.section_name} ({placement.asset_id})
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-[11px] text-[#6b7280]">This asset will replace only the selected page placeholder.</p>
              </div>
            </>
          ) : (
            <p className="rounded-md border border-amber-400/20 bg-amber-400/10 px-3 py-2 text-xs text-amber-200">
              Create and approve a page first to select an exact placement. This asset will stay in your library until then.
            </p>
          )}
          <div>
            <label className="mb-1 block text-xs text-[#6b7280]">Asset Name / ID</label>
            <input
              type="text"
              value={form.asset_id}
              onChange={(e) => setForm((f) => ({ ...f, asset_id: e.target.value }))}
              placeholder="hero_background"
              className="w-full rounded-md border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none placeholder:text-[#4a5260] focus:border-[#d3ff72]/50"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-[#6b7280]">Image Prompt</label>
            <textarea
              rows={3}
              value={form.prompt}
              onChange={(e) => setForm((f) => ({ ...f, prompt: e.target.value }))}
              placeholder="A sweeping mountain landscape at golden hour, photorealistic..."
              className="w-full resize-none rounded-md border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none placeholder:text-[#4a5260] focus:border-[#d3ff72]/50"
            />
          </div>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="mb-1 block text-xs text-[#6b7280]">Width (px)</label>
              <input
                type="number"
                value={form.width}
                onChange={(e) => setForm((f) => ({ ...f, width: e.target.value }))}
                className="w-full rounded-md border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-[#d3ff72]/50"
              />
            </div>
            <div className="flex-1">
              <label className="mb-1 block text-xs text-[#6b7280]">Height (px)</label>
              <input
                type="number"
                value={form.height}
                onChange={(e) => setForm((f) => ({ ...f, height: e.target.value }))}
                className="w-full rounded-md border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-[#d3ff72]/50"
              />
            </div>
          </div>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-md border border-white/10 px-4 py-2 text-sm text-[#a9b0bb] transition hover:bg-white/5"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={!form.asset_id.trim() || !form.prompt.trim() || (effectivePlacements.length > 0 && !form.target_asset_id)}
            className="rounded-md bg-[#d3ff72] px-5 py-2 text-sm font-semibold text-[#12140f] transition hover:bg-[#c2f25b] disabled:opacity-50"
          >
            Add Asset
          </button>
        </div>
      </div>
    </div>
  )
}

export default function AssetStudio({ sessionId, prompt, onClose, onSession, onGenerated }: Props) {
  const [assets, setAssets] = useState<AssetPlan[]>([])
  const [livePlacements, setLivePlacements] = useState<PagePlacement[]>([])
  const [loading, setLoading] = useState(!!sessionId)
  const [busy, setBusy] = useState<string | null>(null)
  const [injecting, setInjecting] = useState(false)
  const [error, setError] = useState("")
  const [showAddModal, setShowAddModal] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploadTarget, setUploadTarget] = useState<string | null>(null)
  const [chatInputs, setChatInputs] = useState<Record<string, string>>({})
  const hydratedStorage = useRef(false)
  const storageKey = `asset-studio:${sessionId || "free"}`

  useEffect(() => {
    if (!hydratedStorage.current) return
    sessionStorage.setItem(storageKey, JSON.stringify(assets))
  }, [assets, storageKey])

  // Fetch live page placements so dropdowns show all data-asset-id slots
  useEffect(() => {
    if (!sessionId) return
    fetch(`/design-sessions/${sessionId}/pages/placements`)
      .then((r) => r.json())
      .then((data) => setLivePlacements(data.placements || []))
      .catch(() => {})
  }, [sessionId])

  // Load the server plan and merge the local draft so switching views does not
  // discard generated URLs, uploads, custom prompts, or parallax choices.
  useEffect(() => {
    if (!sessionId) {
      const saved = sessionStorage.getItem(storageKey)
      if (saved) {
        try {
          setAssets(JSON.parse(saved) as AssetPlan[])
        } catch {
          sessionStorage.removeItem(storageKey)
        }
      }
      hydratedStorage.current = true
      setLoading(false)
      return
    }
    let savedAssets: AssetPlan[] = []
    const saved = sessionStorage.getItem(storageKey)
    if (saved) {
      try {
        savedAssets = JSON.parse(saved) as AssetPlan[]
      } catch {
        sessionStorage.removeItem(storageKey)
      }
    }
    fetch(`/design-sessions/${sessionId}/assets/plan`)
      .then((r) => r.json())
      .then((data) => {
        const savedById = new Map(savedAssets.map((asset) => [asset.asset_id, asset]))
        setAssets((data.assets || []).map((asset: AssetPlan) => ({
          ...asset,
          ...(savedById.get(asset.asset_id) || {}),
          is_parallax: savedById.get(asset.asset_id)?.is_parallax ?? false,
          is_video: savedById.get(asset.asset_id)?.is_video ?? false,
        })))
        hydratedStorage.current = true
        setLoading(false)
      })
      .catch(() => {
        setAssets(savedAssets)
        hydratedStorage.current = true
        setLoading(false)
      })
  }, [sessionId, storageKey])

  const injectAssetList = async (assetList: AssetPlan[]) => {
    if (!sessionId) return
    const payload = {
      assets: assetList.filter((a) => a.url).map((a) => ({
        asset_id: a.asset_id,
        target_asset_id: a.target_asset_id || a.asset_id,
        page_name: a.page_name,
        is_parallax: !!a.is_parallax,
      })),
    }
    const res = await fetch(`/design-sessions/${sessionId}/assets/inject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
    if (!res.ok) return
    const data = await res.json()
    if (data.session) onSession?.(data.session)
  }

  const generateAsset = async (asset: AssetPlan, customPrompt?: string) => {
    setBusy(asset.asset_id)
    setError("")
    const finalPrompt = customPrompt || asset.prompt

    // Use session-scoped endpoint if we have a session, else use a general one
    const url = sessionId
      ? `/design-sessions/${sessionId}/assets/${asset.asset_id}/generate`
      : `/assets/${asset.asset_id}/generate`
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          prompt: asset.prompt,
          edit_request: customPrompt,
          is_video: asset.is_video,
          width: asset.width, 
          height: asset.height 
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Failed to generate")
      setAssets((prev) => {
        const next = prev.map((a) => (a.asset_id === asset.asset_id ? { ...a, url: data.url, prompt: data.revised_prompt || finalPrompt } : a))
        if (sessionId) {
          setTimeout(() => injectAssetList(next), 500)
        }
        return next
      })
      
      // Auto-inject if session exists to update the generated site. This is an
      // intermediate asset action and must not clear the active design session.
    } catch (e: any) {
      setError(e.message || "Generation failed")
    } finally {
      setBusy(null)
    }
  }

  const triggerUpload = (asset_id: string) => {
    setUploadTarget(asset_id)
    fileInputRef.current?.click()
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !uploadTarget) return
    setBusy(uploadTarget)
    const formData = new FormData()
    formData.append("file", file)
    const url = sessionId
      ? `/design-sessions/${sessionId}/assets/${uploadTarget}/upload`
      : `/assets/${uploadTarget}/upload`
    try {
      const res = await fetch(url, { method: "POST", body: formData })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Upload failed")
      setAssets((prev) => {
        const next = prev.map((a) => (a.asset_id === uploadTarget ? { ...a, url: data.url } : a))
        if (sessionId) {
          setTimeout(() => injectAssetList(next), 500)
        }
        return next
      })
    } catch (e: any) {
      setError(e.message || "Upload failed")
    } finally {
      setBusy(null)
      setUploadTarget(null)
      e.target.value = ""
    }
  }

  const toggleParallax = (asset_id: string) => {
    setAssets((prev) =>
      prev.map((a) => (a.asset_id === asset_id ? { ...a, is_parallax: !a.is_parallax } : a))
    )
  }

  const removeAsset = (asset_id: string) => {
    setAssets((prev) => prev.filter((a) => a.asset_id !== asset_id))
  }

  const injectAndFinalizeSilent = async () => {
    if (!sessionId) return
    try {
      await injectAssetList(assets)
    } catch (e) {
      // ignore
    }
  }

  const injectAndFinalize = async () => {
    if (!sessionId) return
    setInjecting(true)
    setError("")
    try {
      await injectAndFinalizeSilent()
      onClose()
    } catch (e: any) {
      setError(e.message || "Something went wrong")
    } finally {
      setInjecting(false)
    }
  }

  const skipAndFinalize = async () => {
    if (!sessionId) { onClose(); return }
    setInjecting(true)
    setError("")
    try {
      const res = await fetch(`/design-sessions/${sessionId}/skip-assets`, { method: "POST" })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Failed to skip")
      onSession?.(data.session as DesignSession)
      onGenerated?.(data.result?.files || {}, prompt || "", data.result?.preview_url || "/generated-preview/")
      onClose()
    } catch (e: any) {
      setError(e.message || "Something went wrong")
    } finally {
      setInjecting(false)
    }
  }

  const readyCount = assets.filter((a) => a.url).length

  return (
    <div className="relative flex h-full flex-col bg-[#07080b] text-[#f7f2e8]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_12%_10%,rgba(211,255,114,0.08),transparent_30rem),radial-gradient(circle_at_85%_5%,rgba(97,157,255,0.1),transparent_32rem)]" />

      <input type="file" className="hidden" ref={fileInputRef} onChange={handleFileChange} accept="image/*" />
      {showAddModal && (
        <AddAssetModal
          placements={assets.filter((asset) => !asset.target_asset_id)}
          livePlacements={livePlacements}
          onAdd={(a) => setAssets((prev) => [...prev, a])}
          onClose={() => setShowAddModal(false)}
        />
      )}

      {/* Top Navigation */}
      <header className="relative z-10 flex items-center justify-between gap-4 border-b border-white/10 bg-[#0a0b0f]/80 px-6 py-4 backdrop-blur-xl">
        <div className="flex items-center gap-4">
          <button
            onClick={onClose}
            className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-[#a9b0bb] transition hover:bg-white/10 hover:text-white"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5M12 5l-7 7 7 7" />
            </svg>
            Back to Design
          </button>
          <div className="h-5 w-px bg-white/10" />
          <div>
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-[#d3ff72]" />
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[#d3ff72]">Asset Studio</span>
              {!sessionId && (
                <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-2 py-0.5 text-[10px] font-medium text-amber-300">
                  Free Mode — no session
                </span>
              )}
            </div>
            <p className="mt-0.5 max-w-md truncate text-sm text-[#fffaf0]">
              {sessionId ? (prompt || "Managing assets") : "Generate images independently — no pages required"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {assets.length > 0 && (
            <span className="text-sm text-[#6b7280]">{readyCount} / {assets.length} ready</span>
          )}
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5 rounded-lg border border-white/15 bg-white/8 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/15"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            Add Asset
          </button>
          {sessionId && (
            <>
              <button
                onClick={skipAndFinalize}
                disabled={injecting}
                className="rounded-lg border border-white/15 bg-white/8 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/15 disabled:opacity-50"
              >
                Skip Assets
              </button>
              <button
                onClick={injectAndFinalize}
                disabled={injecting || assets.length === 0}
                className="flex items-center gap-2 rounded-lg bg-[#d3ff72] px-5 py-2 text-sm font-semibold text-[#12140f] transition hover:bg-[#c2f25b] disabled:opacity-50"
              >
                {injecting ? (
                  <><div className="h-4 w-4 animate-spin rounded-full border-2 border-t-transparent border-[#12140f]" />Injecting...</>
                ) : (
                  <><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>Inject & Finalize</>
                )}
              </button>
            </>
          )}
        </div>
      </header>

      {error && (
        <div className="relative z-10 border-b border-red-400/20 bg-red-500/10 px-6 py-3 text-sm text-red-200">{error}</div>
      )}

      {/* Body */}
      <div className="relative z-10 flex-1 overflow-y-auto px-6 py-8">
        {loading ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-2 border-t-[#d3ff72] border-white/10" />
              <p className="text-[#a9b0bb]">Scanning code for image placeholders...</p>
            </div>
          </div>
        ) : assets.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <div className="rounded-full bg-white/5 p-5">
              <svg className="h-10 w-10 text-[#5b6470]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <p className="font-medium text-[#fffaf0]">
                {sessionId ? "No image placeholders found in your pages" : "No assets yet"}
              </p>
              <p className="mt-1 text-sm text-[#6b7280]">
                {sessionId
                  ? "Your pages don't have any tagged image placeholders to manage."
                  : "Click \"Add Asset\" above to create your first image — no pages needed!"}
              </p>
            </div>
            <button
              onClick={() => setShowAddModal(true)}
              className="mt-2 flex items-center gap-2 rounded-lg bg-[#d3ff72] px-6 py-2.5 text-sm font-semibold text-[#12140f] hover:bg-[#c2f25b]"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
              </svg>
              Add Your First Asset
            </button>
          </div>
        ) : (
          <>
            <div className="mb-6">
              <h1 className="text-xl font-semibold text-[#fffaf0]">
                {sessionId ? "Manage Site Assets" : "Image Generator"}
              </h1>
              <p className="mt-1 text-sm text-[#6b7280]">
                {sessionId
                  ? "Generate or upload images for each placeholder, toggle parallax, then click Inject & Finalize."
                  : "Generate images freely. Click Add Asset to start, then use AI generation or upload your own."}
              </p>
            </div>

            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {assets.map((asset) => (
                <div key={asset.asset_id} className="group flex flex-col overflow-hidden rounded-xl border border-white/10 bg-[#0f1015]/80 backdrop-blur-sm transition hover:border-white/20">
                  {/* Image preview */}
                  <div className="relative aspect-video overflow-hidden bg-black/50">
                    {asset.url ? (
                      asset.url.endsWith(".mp4") ? (
                        <video src={`${asset.url}?t=${Date.now()}`} autoPlay loop muted className="h-full w-full object-cover" />
                      ) : (
                        <img src={`${asset.url}?t=${Date.now()}`} alt={asset.prompt} className="h-full w-full object-cover" />
                      )
                    ) : (
                      <div className="flex h-full w-full flex-col items-center justify-center gap-1 text-[#4a5260]">
                        <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        <span className="text-xs">{asset.width} × {asset.height}</span>
                      </div>
                    )}
                    {busy === asset.asset_id && (
                      <div className="absolute inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm">
                        <div className="h-8 w-8 animate-spin rounded-full border-2 border-t-[#d3ff72] border-white/20" />
                      </div>
                    )}
                    {asset.url && busy !== asset.asset_id && (
                      <div className="absolute right-2 top-2 flex items-center gap-1 rounded-full bg-[#d3ff72]/90 px-2 py-0.5 text-[10px] font-semibold text-[#12140f]">
                        <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                        Ready
                      </div>
                    )}
                    {/* Delete */}
                    <button
                      onClick={() => removeAsset(asset.asset_id)}
                      className="absolute left-2 top-2 hidden rounded p-1 bg-black/50 text-white/60 hover:text-red-400 group-hover:flex"
                      title="Remove asset"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                  </div>

                  {/* Card body */}
                  <div className="flex flex-1 flex-col p-4">
                    <div className="mb-1 flex items-center justify-between">
                      <span className="font-mono text-xs text-[#d3ff72]">{asset.asset_id}</span>
                      <span className="rounded-full bg-white/5 px-2 py-0.5 text-[10px] text-[#6b7280]">{asset.page_name}</span>
                    </div>

                    {/* Inline Page + Section Placement Selector */}
                    {livePlacements.length > 0 && (
                      <div className="mb-3 space-y-1.5 rounded-lg border border-white/8 bg-black/20 p-2">
                        <p className="text-[10px] font-medium uppercase tracking-wider text-[#6b7280]">Placement</p>
                        <div className="flex gap-1.5">
                          <select
                            value={livePlacements.find((p) => p.sections.some((s) => s.asset_id === asset.target_asset_id))?.page_name || ""}
                            onChange={(e) => {
                              setAssets((prev) => prev.map((a) =>
                                a.asset_id === asset.asset_id
                                  ? { ...a, target_asset_id: undefined, page_name: e.target.value }
                                  : a
                              ))
                            }}
                            className="flex-1 min-w-0 rounded border border-white/10 bg-black/40 px-2 py-1 text-[11px] text-white outline-none focus:border-[#d3ff72]/50"
                          >
                            <option value="">— Page —</option>
                            {livePlacements.map((p) => (
                              <option key={p.page_name} value={p.page_name}>{p.page_name}</option>
                            ))}
                          </select>
                          <select
                            value={asset.target_asset_id || ""}
                            onChange={(e) => {
                              const sel = e.target.value
                              const matchedPage = livePlacements.find((p) => p.sections.some((s) => s.asset_id === sel))
                              const matchedSection = matchedPage?.sections.find((s) => s.asset_id === sel)
                              setAssets((prev) => prev.map((a) =>
                                a.asset_id === asset.asset_id
                                  ? { ...a, target_asset_id: sel || undefined, page_name: matchedPage?.page_name || a.page_name, section_name: matchedSection?.section_name || a.section_name }
                                  : a
                              ))
                            }}
                            className="flex-1 min-w-0 rounded border border-white/10 bg-black/40 px-2 py-1 text-[11px] text-white outline-none focus:border-[#d3ff72]/50"
                          >
                            <option value="">— Section —</option>
                            {(livePlacements.find((p) => p.page_name === (livePlacements.find((pg) => pg.sections.some((s) => s.asset_id === asset.target_asset_id))?.page_name || asset.page_name))?.sections || []).map((s) => (
                              <option key={s.asset_id} value={s.asset_id}>{s.section_name}</option>
                            ))}
                          </select>
                        </div>
                        {asset.target_asset_id && (
                          <p className="text-[10px] text-[#d3ff72]/70">✓ mapped to <span className="font-mono">{asset.target_asset_id}</span></p>
                        )}
                      </div>
                    )}

                    <p className="mb-4 line-clamp-2 flex-1 text-xs text-[#a9b0bb]" title={asset.prompt}>{asset.prompt}</p>

                    {/* Options */}
                    <div className="mb-3 flex items-center gap-4">
                      <label className="flex cursor-pointer items-center gap-2 text-xs text-[#8a929e]">
                        <div
                          onClick={() => toggleParallax(asset.asset_id)}
                          className={`relative h-4 w-7 rounded-full transition-colors ${asset.is_parallax ? "bg-[#d3ff72]" : "bg-white/15"}`}
                        >
                          <div className={`absolute top-0.5 h-3 w-3 rounded-full bg-white shadow transition-transform ${asset.is_parallax ? "translate-x-3" : "translate-x-0.5"}`} />
                        </div>
                        Parallax
                      </label>
                      <label className="flex cursor-pointer items-center gap-2 text-xs text-[#8a929e]">
                        <div
                          onClick={() => setAssets(prev => prev.map(a => a.asset_id === asset.asset_id ? { ...a, is_video: !a.is_video } : a))}
                          className={`relative h-4 w-7 rounded-full transition-colors ${asset.is_video ? "bg-[#9d72ff]" : "bg-white/15"}`}
                        >
                          <div className={`absolute top-0.5 h-3 w-3 rounded-full bg-white shadow transition-transform ${asset.is_video ? "translate-x-3" : "translate-x-0.5"}`} />
                        </div>
                        Video Mode
                      </label>
                    </div>

                    {/* Chat Editing */}
                    <div className="mb-3 flex overflow-hidden rounded-md border border-white/10 bg-black/30 focus-within:border-[#d3ff72]/50">
                      <input
                        type="text"
                        value={chatInputs[asset.asset_id] || ""}
                        onChange={(e) => setChatInputs((prev) => ({ ...prev, [asset.asset_id]: e.target.value }))}
                        placeholder="E.g. make the background darker..."
                        className="w-full bg-transparent px-3 py-1.5 text-xs text-white outline-none placeholder:text-[#4a5260]"
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && chatInputs[asset.asset_id]) {
                            generateAsset(asset, chatInputs[asset.asset_id])
                            setChatInputs(prev => ({ ...prev, [asset.asset_id]: "" }))
                          }
                        }}
                      />
                      <button
                        onClick={() => {
                          if (chatInputs[asset.asset_id]) {
                            generateAsset(asset, chatInputs[asset.asset_id])
                            setChatInputs(prev => ({ ...prev, [asset.asset_id]: "" }))
                          }
                        }}
                        className="bg-white/5 px-3 text-[#d3ff72] hover:bg-white/10"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6" /></svg>
                      </button>
                    </div>

                    {/* Action buttons */}
                    <div className="flex gap-2">
                      <button
                        onClick={() => generateAsset(asset)}
                        disabled={busy !== null}
                        className={`flex-1 rounded-md py-1.5 text-xs font-medium text-white transition hover:bg-white/15 disabled:opacity-40 ${asset.is_video ? "bg-[#9d72ff]/20 text-[#d9c2ff] hover:bg-[#9d72ff]/40" : "bg-white/8"}`}
                      >
                        {busy === asset.asset_id ? "..." : (asset.is_video ? "Generate Video" : "Generate AI")}
                      </button>
                      <button
                        onClick={() => triggerUpload(asset.asset_id)}
                        disabled={busy !== null}
                        className="flex-1 rounded-md bg-white/8 py-1.5 text-xs font-medium text-white transition hover:bg-white/15 disabled:opacity-40"
                      >
                        Upload
                      </button>
                    </div>
                  </div>
                </div>
              ))}

              {/* Add new card shortcut */}
              <button
                onClick={() => setShowAddModal(true)}
                className="flex aspect-auto min-h-48 flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-white/10 bg-transparent text-[#4a5260] transition hover:border-[#d3ff72]/30 hover:text-[#d3ff72]"
              >
                <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
                </svg>
                <span className="text-sm font-medium">Add Asset</span>
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
