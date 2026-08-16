import React, { useEffect, useState } from 'react';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import WorkspaceOverview from './components/WorkspaceOverview';
import ChatPanel from './components/ChatPanel';
import AssetsStudio from './components/AssetsStudio';
import { Loader2 } from 'lucide-react';

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

export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'projects' | 'chats' | 'assets' | 'settings'>('dashboard');
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [newProjectName, setNewProjectName] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [openPreviewSignal, setOpenPreviewSignal] = useState(0);
  const [chatProjectId, setChatProjectId] = useState<string>('');
  const [chatMode, setChatMode] = useState<'project' | 'add_page'>('project');
  const [chatModeSignal, setChatModeSignal] = useState(0);
  const [assetPage, setAssetPage] = useState<ProjectPage | null>(null);

  // Fetch projects dynamically from FastAPI backend
  const fetchProjects = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/projects');
      const data = await response.json();
      setProjects(data.projects || []);
    } catch (error) {
      console.error('Error fetching projects:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    try {
      setIsCreating(true);
      const response = await fetch(`/api/projects?name=${encodeURIComponent(newProjectName)}`, {
        method: 'POST',
      });
      if (response.ok) {
        setNewProjectName('');
        fetchProjects(); // Refresh the list dynamically
      }
    } catch (error) {
      console.error('Error creating project:', error);
    } finally {
      setIsCreating(false);
    }
  };

  // Find currently selected project details
  const currentProject = projects.find(p => p.id === selectedProjectId);

  return (
    <div className="flex min-h-screen bg-[#07060d] text-gray-100 font-sans selection:bg-purple-600 selection:text-white">
      
      {/* Modular Sidebar */}
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Panel Content - all tabs always mounted, toggled via CSS */}
      <main className="flex-1 p-8 overflow-y-auto">

        {/* 1. Dashboard Tab */}
        <div className={activeTab === 'dashboard' ? 'block' : 'hidden'}>
          <Dashboard 
            projects={projects}
            loading={loading}
            newProjectName={newProjectName}
            setNewProjectName={setNewProjectName}
            isCreating={isCreating}
            handleCreateProject={handleCreateProject}
            onOpenProject={(id) => {
              setSelectedProjectId(id);
              setActiveTab('projects');
            }}
            fetchProjects={fetchProjects}
          />
        </div>

        {/* 2. Projects & Workspace Tab */}
        <div className={activeTab === 'projects' ? 'block' : 'hidden'}>
          <div className="max-w-6xl mx-auto space-y-8">
            {!selectedProjectId ? (
              // All Projects Directory View
              <div>
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-100 font-rajdhani">All Projects</h2>
                    <p className="text-sm text-gray-400 mt-1">Manage and view active workspaces</p>
                  </div>
                </div>

                {loading ? (
                  <div className="flex justify-center py-12">
                    <Loader2 className="animate-spin text-purple-500" size={32} />
                  </div>
                ) : projects.length === 0 ? (
                  <div className="text-center py-12 border border-dashed border-purple-950/20 rounded-lg">
                    <p className="text-sm text-gray-400">No active projects found.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {projects.map((project) => (
                      <div 
                        key={project.id}
                        onClick={() => setSelectedProjectId(project.id)}
                        className="bg-[#0e0c1f]/40 border border-purple-950/30 hover:border-purple-500/50 rounded-xl p-6 transition-all hover:translate-y-[-2px] cursor-pointer group"
                      >
                        <h3 className="font-bold text-lg text-gray-200 group-hover:text-purple-400 transition-colors">{project.name}</h3>
                        <p className="text-xs text-gray-500 mt-1">{project.pages} pages - {project.status}</p>
                        <div className="mt-6 flex justify-between items-center text-xs border-t border-purple-950/25 pt-4">
                          <span className="text-gray-600">Updated: {new Date(project.last_updated).toLocaleDateString()}</span>
                          <span className="text-purple-400 font-semibold flex items-center gap-1">Open Workspace -&gt;</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              // Workspace detail
              currentProject ? (
                <WorkspaceOverview
                    project={currentProject}
                    onBack={() => setSelectedProjectId(null)}
                    onOpenAssets={(page) => {
                      setAssetPage(page || null);
                      setActiveTab("assets");
                    }}
                    onAddPage={() => {
                      setChatProjectId(currentProject.id);
                      setChatMode('add_page');
                      setChatModeSignal(prev => prev + 1);
                      setActiveTab('chats');
                    }}
                    openPreviewSignal={openPreviewSignal}
                />
              ) : (
                <p className="text-red-400 text-sm">Project workspace not found.</p>
              )
            )}
          </div>
        </div>

        {/* 3. Chats Tab */}
        <div className={activeTab === 'chats' ? 'block' : 'hidden'}>
          <ChatPanel
            projects={projects}
            fetchProjects={fetchProjects}
            initialProjectId={chatProjectId}
            initialMode={chatMode}
            modeSignal={chatModeSignal}
          />
        </div>

        {/* 4. Assets Tab */}
        <div className={activeTab === 'assets' ? 'block' : 'hidden'}>
          {selectedProjectId ? (
            <AssetsStudio
              projectId={selectedProjectId}
              pageName={assetPage?.page_name}
              pageRoute={assetPage?.route}
              onOpenPreview={() => {
                setActiveTab("projects");
                setOpenPreviewSignal(prev => prev + 1);
              }}
            />
          ) : (
            <div className="max-w-4xl mx-auto py-12 text-center border border-dashed border-purple-950/20 rounded-xl bg-[#0b0a16]">
              <p className="text-sm text-gray-400">Please select or open a project workspace first to view its Assets Studio.</p>
            </div>
          )}
        </div>

        {/* 5. Settings Tab placeholder */}
        <div className={activeTab === 'settings' ? 'block' : 'hidden'}>
          <div className="max-w-4xl mx-auto py-12 text-center">
            <h3 className="text-lg font-bold text-gray-200 uppercase tracking-wider mb-2">Settings</h3>
            <p className="text-sm text-gray-400">Settings panel will be implemented in the next step.</p>
          </div>
        </div>

      </main>

    </div>
  );
}
