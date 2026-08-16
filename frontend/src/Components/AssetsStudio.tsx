import { useState, useEffect } from 'react';
import { 
  Upload, 
  Image as ImageIcon, 
  Loader2, 
  FileImage,
  Search,
  Filter,
  SlidersHorizontal,
  Grid,
  List,
  Sparkles,
  Plus,
  ExternalLink,
  Info,
  X,
  Shapes,
  Globe,
  Palette,
  LayoutTemplate,
  Library,
  Trash2,
  CheckCircle2
} from 'lucide-react';


interface Asset {
  id: string;
  name: string;
  page_name?: string | null;
  type: string;
  purpose: string;
  dimensions: string;
  status: string;
  url: string | null;
}

type FilterTab = 'all' | 'image' | 'icon' | 'logo' | 'illustration' | 'svg_diagram' | 'background' | 'approved';

// Returns the appropriate icon component for each asset type
const assetTypeIcon = (type: string) => {
  switch (type) {
    case 'icon':        return <Shapes size={10} />;
    case 'logo':        return <Globe size={10} />;
    case 'illustration': return <Palette size={10} />;
    case 'svg_diagram': return <LayoutTemplate size={10} />;
    case 'background':  return <ImageIcon size={10} />;
    default:            return <ImageIcon size={10} />; // image
  }
};

// Returns a human-readable label for each asset type
const assetTypeLabel = (type: string) => {
  switch (type) {
    case 'icon':        return 'Icon';
    case 'logo':        return 'Logo';
    case 'illustration': return 'Illustration';
    case 'svg_diagram': return 'SVG Diagram';
    case 'background':  return 'Background';
    default:            return 'Image';
  }
};

// Whether this type can be AI-generated (as opposed to library sourced)
const isGeneratable = (type: string) =>
  ['image', 'illustration', 'svg_diagram', 'background'].includes(type);

// Whether this type comes from a library (no local file expected)
const isLibraryType = (type: string) => ['icon', 'logo'].includes(type);

interface AssetsStudioProps {
  projectId: string;
  pageName?: string;
  pageRoute?: string;
  onOpenPreview: () => void;
}

export default function AssetsStudio({ projectId, pageName, pageRoute, onOpenPreview }: AssetsStudioProps) {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [uploadingAssetId, setUploadingAssetId] = useState<string | null>(null);
  const [deletingAssetId, setDeletingAssetId] = useState<string | null>(null);
  const [approvingAssetId, setApprovingAssetId] = useState<string | null>(null);
  const [applyingAssets, setApplyingAssets] = useState(false);
  
  // Navigation filters
  const [activeFilter, setActiveFilter] = useState<FilterTab>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // AI Generator Modal States
  const [showGenModal, setShowGenModal] = useState(false);
  const [genAssetId, setGenAssetId] = useState('');
  const [customPrompt, setCustomPrompt] = useState('');
  const [customWidth, setCustomWidth] = useState(1024);
  const [customHeight, setCustomHeight] = useState(1024);
  const [generating, setGenerating] = useState(false);
  
  useEffect(() => {
    fetchAssets();
  }, [projectId, pageName]);

  const fetchAssets = async () => {
    try {
      setLoading(true);
      const params = pageName ? `?page_name=${encodeURIComponent(pageName)}` : '';
      const response = await fetch(`/api/projects/${projectId}/assets${params}`);
      const data = await response.json();
      setAssets(data.assets || []);
    } catch (error) {
      console.error("Error fetching assets:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (assetId: string, event: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = event.target.files;
    if (!fileList || fileList.length === 0) return;

    const file = fileList[0];
    const formData = new FormData();
    formData.append("file", file);

    try {
      setUploadingAssetId(assetId);
      const params = new URLSearchParams({ asset_id: assetId });
      if (pageName) params.set('page_name', pageName);
      const response = await fetch(`/api/projects/${projectId}/assets/upload?${params.toString()}`, {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        fetchAssets(); // Refresh grid layout on success
      } else {
        alert("Upload failed.");
      }
    } catch (error) {
      console.error("Error uploading file:", error);
    } finally {
      setUploadingAssetId(null);
    }
  };

  // Triggers Pollinations Image Generation backend endpoint
  const handleGenerateAsset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customPrompt.trim() || !genAssetId.trim()) return;

    try {
      setGenerating(true);
      const response = await fetch(`/api/projects/${projectId}/assets/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          asset_id: genAssetId,
          prompt: customPrompt,
          width: customWidth,
          height: customHeight,
          page_name: pageName || null
        })
      });

      if (response.ok) {
        setShowGenModal(false);
        setCustomPrompt('');
        fetchAssets(); // Refresh dynamic list
      } else {
        alert("Generation failed. Please try a different prompt.");
      }
    } catch (error) {
      console.error("Error generating asset:", error);
    } finally {
      setGenerating(false);
    }
  };

  const handleDeleteAsset = async (asset: Asset) => {
    const confirmed = window.confirm(`Delete "${asset.name}" from this project?`);
    if (!confirmed) return;

    try {
      setDeletingAssetId(asset.id);
      const response = await fetch(`/api/projects/${projectId}/assets/${encodeURIComponent(asset.id)}`, {
        method: "DELETE",
      });

      if (response.ok) {
        setAssets(prev => prev.filter(item => item.id !== asset.id));
      } else {
        alert("Delete failed.");
      }
    } catch (error) {
      console.error("Error deleting asset:", error);
      alert("Delete failed.");
    } finally {
      setDeletingAssetId(null);
    }
  };

  const handleToggleApproval = async (asset: Asset, approved: boolean) => {
    try {
      setApprovingAssetId(asset.id);
      const response = await fetch(`/api/projects/${projectId}/assets/${encodeURIComponent(asset.id)}/approval`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Approval update failed.");
      }

      const updatedAsset = await response.json();
      setAssets(prev => prev.map(item => item.id === asset.id ? updatedAsset : item));
    } catch (error: any) {
      console.error("Error updating approval:", error);
      alert(error?.message || "Approval update failed.");
    } finally {
      setApprovingAssetId(null);
    }
  };

  const handleApplyApprovedAssets = async () => {
    const approvedCount = assets.filter(asset => asset.status === "Approved").length;
    if (approvedCount === 0) {
      alert("Select at least one asset before applying.");
      return;
    }

    try {
      setApplyingAssets(true);
      const params = pageName ? `?page_name=${encodeURIComponent(pageName)}` : '';
      const response = await fetch(`/api/projects/${projectId}/inject-assets${params}`, {
        method: "POST",
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Asset injection failed.");
      }

      onOpenPreview();
    } catch (error: any) {
      console.error("Error applying approved assets:", error);
      alert(error?.message || "Asset injection failed.");
    } finally {
      setApplyingAssets(false);
    }
  };

  const handleGeneratePageAssets = async () => {
    try {
      setGenerating(true);
      const params = pageName ? `?page_name=${encodeURIComponent(pageName)}` : '';
      const response = await fetch(`/api/projects/${projectId}/generate-assets${params}`, {
        method: "POST",
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Asset generation failed.");
      }

      fetchAssets();
    } catch (error: any) {
      console.error("Error generating page assets:", error);
      alert(error?.message || "Asset generation failed.");
    } finally {
      setGenerating(false);
    }
  };

  // Filter criteria logic matching tabs & search query
  const filteredAssets = assets.filter(a => {
    const matchesSearch = a.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          a.id.toLowerCase().includes(searchQuery.toLowerCase());
    
    if (activeFilter === 'approved') return matchesSearch && a.status === 'Approved';
    if (activeFilter !== 'all') return matchesSearch && a.type === activeFilter;
    return matchesSearch;
  });

  // Count per tab for the badge display
  const counts: Record<string, number> = {
    all: assets.length,
    image: assets.filter(a => a.type === 'image').length,
    icon: assets.filter(a => a.type === 'icon').length,
    logo: assets.filter(a => a.type === 'logo').length,
    illustration: assets.filter(a => a.type === 'illustration').length,
    svg_diagram: assets.filter(a => a.type === 'svg_diagram').length,
    background: assets.filter(a => a.type === 'background').length,
    approved: assets.filter(a => a.status === 'Approved').length,
  };

  return (
    <div className="w-full space-y-6 bg-[#07060d] text-gray-200 p-6 min-h-[calc(100vh-140px)]">
      
      {/* 1. Header Path & Global Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-purple-950/20 pb-5">
        <div>
          <div className="text-[10px] text-gray-500 font-medium space-x-1.5 mb-1.5">
            <span>Projects</span>
            <span>&gt;</span>
            <span className="text-gray-400">Workspace</span>
            <span>&gt;</span>
            <span className="text-purple-400">Assets</span>
          </div>
          <h2 className="text-2xl font-bold text-gray-100 font-rajdhani">Assets Studio</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Manage, regenerate, upload and approve assets{pageName ? ` for ${pageName}${pageRoute ? ` (${pageRoute})` : ''}` : ''}.
          </p>
        </div>

        {/* Global Action buttons */}
        <div className="flex flex-wrap gap-2">
          <button 
            onClick={() => {
              setGenAssetId(`custom_asset_${Date.now().toString().slice(-4)}`);
              setShowGenModal(true);
            }}
            className="flex items-center gap-1.5 px-4 py-2 border border-purple-950/40 hover:bg-[#15112c] rounded-lg text-xs font-semibold text-gray-300 transition-colors cursor-pointer"
          >
            <Plus size={13} />
            Add Custom Asset
          </button>
          <button
            type="button"
            onClick={handleApplyApprovedAssets}
            disabled={applyingAssets || counts.approved === 0}
            className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-lg shadow-emerald-900/20 transition-all cursor-pointer disabled:opacity-50"
          >
            {applyingAssets ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={13} />}
            Apply Approved Assets
          </button>
          <button
            type="button"
            onClick={handleGeneratePageAssets}
            disabled={generating}
            className="flex items-center gap-1.5 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold shadow-lg shadow-purple-900/20 transition-all cursor-pointer disabled:opacity-50"
          >
            {generating ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
            Generate All Assets
          </button>
        </div>
      </div>

      {/* 2. Tabs Filter Category */}
      <div className="border-b border-purple-950/15 flex justify-between items-center overflow-x-auto">
        <div className="flex gap-5 text-xs font-semibold whitespace-nowrap">
          {([
            { id: 'all',          label: 'All Assets' },
            { id: 'image',        label: 'Images' },
            { id: 'background',   label: 'Backgrounds' },
            { id: 'illustration', label: 'Illustrations' },
            { id: 'svg_diagram',  label: 'SVG Diagrams' },
            { id: 'icon',         label: 'Icons' },
            { id: 'logo',         label: 'Logos' },
            { id: 'approved',     label: 'Approved' },
          ] as { id: FilterTab; label: string }[]).map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveFilter(tab.id)}
              className={`pb-3.5 border-b-2 transition-all cursor-pointer flex items-center gap-1.5 ${
                activeFilter === tab.id 
                  ? 'border-purple-600 text-purple-400 font-bold' 
                  : 'border-transparent text-gray-500 hover:text-gray-300'
              }`}
            >
              {tab.label}
              {counts[tab.id] > 0 && (
                <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-purple-950/40 text-purple-400 font-bold">
                  {counts[tab.id]}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* 3. Toolbar: Search / Sorting */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
        {/* Search */}
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-2.5 text-gray-500" size={14} />
          <input
            type="text"
            placeholder="Search assets..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#0d0c20]/60 border border-purple-950/30 rounded-lg pl-9 pr-4 py-2 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-600 transition-all"
          />
        </div>

        {/* Filters and View toggles */}
        <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
          <button className="flex items-center gap-1.5 px-3.5 py-2 bg-[#0e0c1f] hover:bg-[#15112c] border border-purple-950/30 rounded-lg text-xs font-semibold text-gray-300 cursor-pointer">
            <Filter size={12} />
            Filter
          </button>
          
          <button className="flex items-center gap-1.5 px-3.5 py-2 bg-[#0e0c1f] hover:bg-[#15112c] border border-purple-950/30 rounded-lg text-xs font-semibold text-gray-300 cursor-pointer">
            <SlidersHorizontal size={12} />
            Sort: Newest
          </button>

          <div className="flex bg-[#0e0c1f] p-1 border border-purple-950/30 rounded-lg ml-2">
            <button className="p-1.5 rounded text-purple-400 bg-purple-950/30 border border-purple-900/30 cursor-pointer">
              <Grid size={12} />
            </button>
            <button className="p-1.5 rounded text-gray-500 hover:text-gray-300 cursor-pointer">
              <List size={12} />
            </button>
          </div>
        </div>
      </div>

      {/* 4. Asset Grid Layout */}
      {loading ? (
        <div className="flex justify-center py-24">
          <Loader2 className="animate-spin text-purple-500" size={32} />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {filteredAssets.map((asset) => {
            const isApproved = asset.status === 'Approved';
            const isUploading = uploadingAssetId === asset.id;
            const isDeleting = deletingAssetId === asset.id;
            const isApproving = approvingAssetId === asset.id;

            return (
              <div 
                key={asset.id}
                className="bg-[#0b0a16] border border-purple-950/20 rounded-xl overflow-hidden shadow-lg flex flex-col justify-between group hover:border-purple-600/30 transition-all min-h-[280px]"
              >
                {/* Visual Image Area */}
                <div className="h-44 bg-[#07060c] relative flex items-center justify-center border-b border-purple-950/15 overflow-hidden">
                  
                  {/* Select Checkbox (top-left) */}
                  <input 
                    type="checkbox" 
                    checked={isApproved}
                    disabled={isApproving}
                    onChange={(e) => handleToggleApproval(asset, e.target.checked)}
                    className="absolute top-3.5 left-3.5 z-10 w-3.5 h-3.5 rounded border-purple-950 bg-[#0d0c20]/60 text-purple-600 focus:ring-0 focus:ring-offset-0 cursor-pointer"
                    title="Select asset for injection"
                  />

                  {/* Type indicator badge (top-right) */}
                  <div className="absolute top-3 right-3 z-10 p-1.5 bg-[#0d0c20]/60 border border-purple-950/30 rounded-md text-gray-400">
                    {assetTypeIcon(asset.type)}
                  </div>

                  {asset.url ? (
                    <img 
                      src={asset.url} 
                      alt={asset.name} 
                      className={`w-full h-full object-cover transition-all duration-300 group-hover:scale-105 ${isApproved ? '' : 'opacity-70'}`}
                    />
                  ) : isLibraryType(asset.type) ? (
                    // Icons/logos come from libraries — no local file expected
                    <div className="flex flex-col items-center gap-2 text-purple-700">
                      <Library size={28} />
                      <span className="text-[9px] uppercase font-bold tracking-wider text-purple-500">From Library</span>
                      <span className="text-[9px] text-gray-600">{assetTypeLabel(asset.type)}</span>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-2 text-gray-600">
                      <FileImage size={28} />
                      <span className="text-[9px] uppercase font-bold tracking-wider">Not Yet Generated</span>
                      <span className="text-[9px] text-gray-700">{assetTypeLabel(asset.type)}</span>
                    </div>
                  )}
                </div>

                {/* Info and Actions */}
                <div className="p-4 flex flex-col justify-between flex-1 bg-[#0b0a16]">
                  <div>
                    <h4 className="font-semibold text-xs text-gray-200 truncate">{asset.name}</h4>
                    <p className="text-[10px] text-gray-500 mt-1 line-clamp-1">{asset.purpose}</p>
                  </div>

                  <div className="mt-4">
                    {/* Dimension and Status */}
                    <div className="flex justify-between items-center text-[10px] text-gray-500 font-medium mb-3">
                      <span>{asset.dimensions}</span>
                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${
                        isApproved 
                          ? 'bg-emerald-950/20 text-emerald-400 border border-emerald-900/30'
                          : 'bg-amber-950/20 text-amber-400 border border-amber-900/30'
                      }`}>
                        {asset.status}
                      </span>
                    </div>

                    {/* Quick Button Panel */}
                    <div className="grid grid-cols-3 gap-1.5 border-t border-purple-950/10 pt-3">
                      <label className="col-span-1">
                        <input 
                          type="file" 
                          accept="image/*"
                          disabled={isUploading}
                          onChange={(e) => handleFileUpload(asset.id, e)}
                          className="hidden"
                        />
                        <div className="w-full py-1.5 bg-[#0e0c1f] hover:bg-[#15112c] border border-purple-950/30 text-purple-400 hover:text-purple-300 rounded text-[9px] font-bold flex items-center justify-center gap-1 transition-colors cursor-pointer">
                          {isUploading ? <Loader2 size={10} className="animate-spin" /> : <Upload size={10} />}
                          Upload
                        </div>
                      </label>
                      {/* Regenerate only available for generatable types */}
                      {isGeneratable(asset.type) ? (
                        <button 
                          onClick={() => {
                            setGenAssetId(asset.id);
                            setCustomPrompt(asset.purpose);
                            setShowGenModal(true);
                          }}
                          className="col-span-1 py-1.5 bg-[#0e0c1f] hover:bg-[#15112c] border border-purple-950/30 text-purple-400 hover:text-purple-300 rounded text-[9px] font-bold transition-colors cursor-pointer"
                        >
                          Regenerate
                        </button>
                      ) : (
                        <div className="col-span-1 py-1.5 bg-[#0d0c1a] border border-purple-950/10 text-gray-700 rounded text-[9px] font-bold flex items-center justify-center" title="Library sourced — not AI generatable">
                          Library
                        </div>
                      )}
                      <button
                        type="button"
                        disabled={isDeleting}
                        onClick={() => handleDeleteAsset(asset)}
                        className="col-span-1 py-1.5 bg-[#160b12] hover:bg-red-950/30 border border-red-950/30 text-red-400 hover:text-red-300 rounded flex items-center justify-center cursor-pointer disabled:opacity-50"
                        title="Delete asset"
                      >
                        {isDeleting ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                      </button>
                    </div>
                  </div>
                </div>

              </div>
            );
          })}

          {/* 5. Dash border "Add New Asset" Card mockup */}
          <div className="border-2 border-dashed border-purple-950/30 hover:border-purple-600/30 rounded-xl p-6 flex flex-col justify-center items-center text-center bg-[#0b0a16]/20 transition-all min-h-[280px]">
            <div className="p-3 bg-purple-950/10 border border-purple-900/20 rounded-full text-purple-400 mb-4">
              <Plus size={20} />
            </div>
            <h4 className="font-bold text-sm text-gray-200">Add New Asset</h4>
            <p className="text-[10px] text-gray-500 mt-1 max-w-[160px] leading-relaxed">
              Upload your own asset or generate with AI
            </p>
            <label className="mt-5 w-full max-w-[140px]">
              <input 
                type="file" 
                accept="image/*"
                onChange={(e) => handleFileUpload(`uploaded_asset_${Date.now().toString().slice(-4)}`, e)}
                className="hidden"
              />
              <div className="py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold shadow-lg shadow-purple-900/10 transition-colors cursor-pointer flex items-center justify-center gap-1">
                <Upload size={12} />
                Upload Asset
              </div>
            </label>
          </div>
        </div>
      )}

      {/* 5. Bottom Helper Banner */}
      <div className="bg-purple-950/15 border border-purple-900/20 p-4 rounded-xl flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mt-8">
        <div className="flex items-center gap-2 text-purple-400">
          <Info size={14} />
          <p className="text-[10px] text-gray-400">
            Tip: You can upload your own assets or regenerate with different prompts until you are satisfied.
          </p>
        </div>
        <a href="#guide" className="text-[10px] text-purple-400 hover:underline flex items-center gap-0.5 shrink-0">
          View Asset Guidelines
          <ExternalLink size={10} />
        </a>
      </div>

      {/* ========================================== */}
      {/* AI IMAGE GENERATOR MODAL */}
      {/* ========================================== */}
      {showGenModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-[#0b0a16] border border-purple-900/30 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl">
            {/* Header */}
            <div className="px-5 py-4 border-b border-purple-950/25 flex justify-between items-center bg-[#0d0c20]/60">
              <div className="flex items-center gap-2 text-purple-400">
                <Sparkles size={16} />
                <h3 className="font-bold text-sm text-gray-200">AI Image Generator</h3>
              </div>
              <button 
                onClick={() => setShowGenModal(false)}
                className="text-gray-500 hover:text-gray-300 transition-colors cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleGenerateAsset} className="p-5 space-y-4">
              {/* Asset Name ID */}
              <div>
                <label className="block text-[10px] text-gray-500 font-semibold uppercase tracking-wider mb-1">Asset ID</label>
                <input 
                  type="text" 
                  value={genAssetId}
                  onChange={(e) => setGenAssetId(e.target.value)}
                  placeholder="e.g. hero_image"
                  className="w-full bg-[#07060d] border border-purple-950/40 rounded-lg px-3 py-2 text-xs text-gray-300 focus:outline-none focus:border-purple-600"
                  required
                />
              </div>

              {/* Prompt */}
              <div>
                <label className="block text-[10px] text-gray-500 font-semibold uppercase tracking-wider mb-1">Visual Prompt</label>
                <textarea 
                  rows={4}
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  placeholder="Describe the image detail (e.g. A sleek red sports car inside a neon dark hangar, futuristic style, raytracing reflection)..."
                  className="w-full bg-[#07060d] border border-purple-950/40 rounded-lg px-3 py-2 text-xs text-gray-300 focus:outline-none focus:border-purple-600 resize-none"
                  required
                />
              </div>

              {/* Size parameters */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="block text-[10px] text-gray-500 font-semibold uppercase tracking-wider mb-1">Width</label>
                  <select 
                    value={customWidth}
                    onChange={(e) => setCustomWidth(parseInt(e.target.value))}
                    className="w-full bg-[#07060d] border border-purple-950/40 rounded-lg px-3 py-2 text-xs text-gray-300 focus:outline-none focus:border-purple-600 cursor-pointer"
                  >
                    <option value={512}>512 px</option>
                    <option value={1024}>1024 px</option>
                    <option value={1920}>1920 px</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] text-gray-500 font-semibold uppercase tracking-wider mb-1">Height</label>
                  <select 
                    value={customHeight}
                    onChange={(e) => setCustomHeight(parseInt(e.target.value))}
                    className="w-full bg-[#07060d] border border-purple-950/40 rounded-lg px-3 py-2 text-xs text-gray-300 focus:outline-none focus:border-purple-600 cursor-pointer"
                  >
                    <option value={512}>512 px</option>
                    <option value={1024}>1024 px</option>
                    <option value={1080}>1080 px</option>
                  </select>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2 pt-2">
                <button 
                  type="button"
                  onClick={() => setShowGenModal(false)}
                  className="flex-1 py-2 border border-purple-950/40 hover:bg-purple-950/10 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  disabled={generating}
                  className="flex-1 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold shadow-lg shadow-purple-900/10 transition-colors cursor-pointer flex items-center justify-center gap-1.5"
                >
                  {generating ? (
                    <>
                      <Loader2 size={12} className="animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles size={12} />
                      Generate Asset
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
