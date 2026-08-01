import React, { useEffect, useState } from 'react';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import WorkspaceOverview from './components/WorkspaceOverview';
import ChatPanel from './components/ChatPanel';
import { Loader2 } from 'lucide-react';

interface Project {
  id: string;
  name: string;
  pages: number;
  status: string;
  last_updated: string;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'projects' | 'chats' | 'assets' | 'settings'>('dashboard');
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [newProjectName, setNewProjectName] = useState('');
  const [isCreating, setIsCreating] = useState(false);

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

      {/* Main Panel Content */}
      <main className="flex-1 p-8 overflow-y-auto">
        
        {/* 1. Dashboard Tab */}
        {activeTab === 'dashboard' && (
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
        )}

        {/* 2. Projects & Workspace Tab */}
        {activeTab === 'projects' && (
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
                        <p className="text-xs text-gray-500 mt-1">{project.pages} pages • {project.status}</p>
                        <div className="mt-6 flex justify-between items-center text-xs border-t border-purple-950/25 pt-4">
                          <span className="text-gray-600">Updated: {new Date(project.last_updated).toLocaleDateString()}</span>
                          <span className="text-purple-400 font-semibold flex items-center gap-1">Open Workspace →</span>
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
                />
              ) : (
                <p className="text-red-400 text-sm">Project workspace not found.</p>
              )
            )}
          </div>
        )}

        {/* 3. Chats Tab */}
        {activeTab === 'chats' && (
          <ChatPanel projects={projects} fetchProjects={fetchProjects} />
        )}

        {/* Temporary placeholders for remaining tabs */}
        {activeTab !== 'dashboard' && activeTab !== 'projects' && activeTab !== 'chats' && (
          <div className="max-w-4xl mx-auto py-12 text-center">
            <h3 className="text-lg font-bold text-gray-200 uppercase tracking-wider mb-2">{activeTab} tab</h3>
            <p className="text-sm text-gray-400">This layout component will be implemented dynamically in the next step of the plan.</p>
          </div>
        )}

      </main>

    </div>
  );
}
