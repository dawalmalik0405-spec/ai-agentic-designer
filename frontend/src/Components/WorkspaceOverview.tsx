import { useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import PreviewPanel from './PreviewPanel';

interface Project {
  id: string;
  name: string;
  pages: number;
  status: string;
  last_updated: string;
}

interface ProjectPage {
  page_name: string;
  route: string;
  file_path: string;
  module_name: string;
  is_home: boolean;
}

interface WorkspaceOverviewProps {
    project: Project;
    onBack: () => void;
    onOpenAssets: (page?: ProjectPage | null) => void;
    onAddPage: () => void;
    openPreviewSignal?: number;
}

export default function WorkspaceOverview({ project, onBack, onOpenAssets, onAddPage, openPreviewSignal = 0 }: WorkspaceOverviewProps) {
  const [showPreview, setShowPreview] = useState<boolean>(false);
  const [pages, setPages] = useState<ProjectPage[]>([]);
  const [selectedPage, setSelectedPage] = useState<ProjectPage | null>(null);

  const fetchPages = async () => {
    try {
      const response = await fetch(`/api/projects/${project.id}/pages`);
      const data = await response.json();
      const nextPages = data.pages || [];
      setPages(nextPages);
      setSelectedPage(prev => {
        if (prev) {
          const stillExists = nextPages.find((page: ProjectPage) => page.page_name === prev.page_name);
          if (stillExists) return stillExists;
        }
        return nextPages[0] || null;
      });
    } catch (error) {
      console.error('Failed to load project pages:', error);
      setPages([]);
      setSelectedPage(null);
    }
  };

  useEffect(() => {
    fetchPages();
  }, [project.id, project.pages, project.last_updated]);

  useEffect(() => {
    if (openPreviewSignal > 0) {
      setShowPreview(true);
    }
  }, [openPreviewSignal]);

  if (showPreview) {
    return (
      <div className="space-y-4">
        {/* Navigation Header */}
        <div className="flex items-center gap-4 border-b border-purple-950/25 pb-4">
          <button 
            onClick={() => setShowPreview(false)}
            className="text-xs px-3 py-1.5 bg-[#0e0b1d] hover:bg-[#15112c] rounded-lg border border-purple-950/30 text-gray-400 hover:text-gray-200 transition-colors cursor-pointer"
          >
            &lt;- Back to Workspace
          </button>
          <div>
            <h2 className="text-lg font-bold text-gray-100 font-rajdhani">{project.name} Preview</h2>
            <p className="text-[10px] text-gray-500">Live compilation review</p>
          </div>
        </div>

        {/* Modular Preview Window */}
        <PreviewPanel
            projectId={project.id}
            pageName={selectedPage?.page_name}
            pageRoute={selectedPage?.route}
            pageFilePath={selectedPage?.file_path}
            onGenerateAssets={() => onOpenAssets(selectedPage)}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="flex items-center justify-between border-b border-purple-950/25 pb-4">
        <div className="flex items-center gap-4">
          <button 
            onClick={onBack}
            className="text-xs px-3 py-1.5 bg-[#0e0b1d] hover:bg-[#15112c] rounded-lg border border-purple-950/30 text-gray-400 hover:text-gray-200 transition-colors cursor-pointer"
          >
            &lt;- Back to List
          </button>
          <div>
            <h2 className="text-xl font-bold text-gray-100 font-rajdhani">{project.name} Workspace</h2>
            <p className="text-xs text-gray-500">ID: {project.id} - Status: {project.status}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={() => setShowPreview(true)}
            className="px-4 py-2 bg-[#0e0c1f] border border-purple-950/30 hover:bg-[#15112c] rounded-lg text-xs font-semibold transition-colors cursor-pointer"
          >
            Preview Website
          </button>
          <button className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold shadow-lg shadow-purple-900/20 transition-colors cursor-pointer">
            Edit Project
          </button>
        </div>
      </div>

      {/* Overview Panels */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Project Details */}
        <div className="bg-[#0b0a16] border border-purple-950/20 rounded-xl p-5 shadow-lg space-y-4">
          <h4 className="text-sm font-semibold text-gray-300">Project Summary</h4>
          <div className="text-xs text-gray-400 space-y-2">
            <p className="text-gray-500">
              A modern showroom website with premium design, smooth animations, and immersive experiences.
            </p>
            <div className="pt-2 border-t border-purple-950/15">
              <span className="block text-[10px] text-gray-600 uppercase">Created</span>
              <span className="text-gray-300 font-medium">May 18, 2026</span>
            </div>
            <div className="pt-2 border-t border-purple-950/15">
              <span className="block text-[10px] text-gray-600 uppercase">Last Updated</span>
              <span className="text-gray-300 font-medium">{new Date(project.last_updated).toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* Pipeline Process Checklist */}
        <div className="bg-[#0b0a16] border border-purple-950/20 rounded-xl p-5 shadow-lg md:col-span-2">
          <h4 className="text-sm font-semibold text-gray-300 mb-4">Agent Workspace Progress</h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            {[
              { step: "1. Architect Agent", desc: "Define structural layout & goals", done: true },
              { step: "2. Research Agent", desc: "Scrape competitor styles & links", done: true },
              { step: "3. Design System Agent", desc: "Build color palettes & variables", done: true },
              { step: "4. Page Design Agent", desc: "Create structural page specs", done: project.pages > 0 },
              { step: "5. Asset Studio Agent", desc: "Generate assets & edit prompts", done: false },
              { step: "6. Code Generation", desc: "Produce production React + Tailwind code", done: false },
            ].map((stepItem, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-[#0d0c20]/60 border border-purple-950/25 rounded-lg">
                <div>
                  <p className="font-semibold text-gray-200">{stepItem.step}</p>
                  <p className="text-[10px] text-gray-500 mt-0.5">{stepItem.desc}</p>
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] ${
                  stepItem.done 
                    ? 'bg-emerald-950/20 text-emerald-400 border border-emerald-900/40' 
                    : 'bg-purple-950/20 text-purple-400 border border-purple-900/40'
                }`}>
                  {stepItem.done ? "Done" : "Pending"}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Pages Section */}
      <div className="bg-[#0b0a16] border border-purple-950/20 rounded-xl p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-200">Website Pages</h3>
          <button
            type="button"
            onClick={onAddPage}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#0e0c1f] hover:bg-[#15112c] border border-purple-950/30 rounded-lg text-xs font-semibold text-gray-300 transition-colors cursor-pointer"
          >
            <Plus size={14} /> Add Page
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          {pages.map((page) => {
            const isSelected = selectedPage?.page_name === page.page_name;
            return (
              <button
                type="button"
                key={`${page.page_name}-${page.route}`}
                onClick={() => setSelectedPage(page)}
                className={`bg-[#0e0c1f]/50 border rounded-lg p-4 text-center cursor-pointer hover:border-purple-600/40 transition-all flex flex-col justify-between min-h-[120px] group ${
                  isSelected ? 'border-purple-500/70 shadow-lg shadow-purple-950/20' : 'border-purple-950/20'
                }`}
              >
                <div>
                  <h5 className="font-bold text-sm text-gray-200 group-hover:text-purple-400 transition-colors">{page.page_name}</h5>
                  <p className="text-[10px] text-gray-500 mt-1">{page.route === '/' ? '/index' : page.route}</p>
                </div>
                <span className={`text-[10px] font-semibold self-center mt-4 ${isSelected ? 'text-emerald-400' : 'text-purple-400'}`}>
                  {isSelected ? 'Active Page' : 'Select Page'}
                </span>
              </button>
            );
          })}

          {pages.length === 0 && (
            <div className="bg-[#0e0c1f]/20 border border-dashed border-purple-950/20 rounded-lg p-4 text-center flex flex-col justify-center items-center min-h-[120px]">
              <p className="text-xs text-gray-500">No pages generated yet.</p>
              <p className="text-[10px] text-gray-600 mt-1">Generate a project from the Chat Panel first.</p>
            </div>
          )}
        </div>
      </div>

    </div>
  );
}
