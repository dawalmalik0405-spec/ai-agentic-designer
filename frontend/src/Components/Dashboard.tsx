import React from 'react';
import { 
  FolderKanban, 
  Plus, 
  ExternalLink,
  Loader2,
  TrendingUp,
  FileCode,
  Image as ImageIcon 
} from 'lucide-react';

interface Project {
  id: string;
  name: string;
  pages: number;
  status: string;
  last_updated: string;
}

interface DashboardProps {
  projects: Project[];
  loading: boolean;
  newProjectName: string;
  setNewProjectName: (name: string) => void;
  isCreating: boolean;
  handleCreateProject: (e: React.FormEvent) => void;
  onOpenProject: (projectId: string) => void;
  fetchProjects: () => void;
}

export default function Dashboard({
  projects,
  loading,
  newProjectName,
  setNewProjectName,
  isCreating,
  handleCreateProject,
  onOpenProject,
  fetchProjects
}: DashboardProps) {
  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Welcome Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-100 font-rajdhani">Welcome back, John 👋</h2>
          <p className="text-sm text-gray-400 mt-1">Ready to design your next masterpiece?</p>
        </div>

        {/* Quick Project Creation Form */}
        <form onSubmit={handleCreateProject} className="flex gap-2">
          <input
            type="text"
            placeholder="New project name..."
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            className="bg-[#0f0e1d] border border-purple-950/40 rounded-lg px-4 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-600 focus:ring-1 focus:ring-purple-600 transition-all w-60"
          />
          <button
            type="submit"
            disabled={isCreating}
            className="bg-purple-600 hover:bg-purple-700 text-white rounded-lg px-4 py-2 text-sm font-semibold transition-all flex items-center gap-1.5 shadow-lg shadow-purple-900/20 disabled:opacity-50 cursor-pointer"
          >
            {isCreating ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
            New Project
          </button>
        </form>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Projects', value: projects.length, icon: FolderKanban, color: 'text-purple-400' },
          { label: 'Websites Built', value: projects.filter(p => p.status === 'Completed').length, icon: FileCode, color: 'text-emerald-400' },
          { label: 'In Progress', value: projects.filter(p => p.status === 'In Progress').length, icon: TrendingUp, color: 'text-indigo-400' },
          { label: 'Global Assets', value: projects.reduce((acc, p) => acc + p.pages * 4, 0), icon: ImageIcon, color: 'text-amber-400' },
        ].map((stat, idx) => {
          const Icon = stat.icon;
          return (
            <div key={idx} className="bg-[#0c0a18] border border-purple-950/20 rounded-xl p-5 shadow-lg flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-400 font-medium uppercase tracking-wider">{stat.label}</p>
                <p className="text-3xl font-bold mt-2 text-gray-100">{stat.value}</p>
              </div>
              <div className={`p-3 bg-purple-950/20 border border-purple-900/20 rounded-lg ${stat.color}`}>
                <Icon size={20} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Projects List Section */}
      <div className="bg-[#0b0a16] border border-purple-950/20 rounded-xl p-6 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-md font-semibold text-gray-200">Recent Workspaces</h3>
          <button 
            type="button"
            onClick={fetchProjects} 
            className="text-xs text-purple-400 hover:text-purple-300 font-medium transition-colors cursor-pointer"
          >
            Refresh List
          </button>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-400 gap-2">
            <Loader2 className="animate-spin text-purple-500" size={32} />
            <p className="text-sm font-medium">Fetching database details...</p>
          </div>
        ) : projects.length === 0 ? (
          <div className="text-center py-12 border border-dashed border-purple-950/20 rounded-lg">
            <p className="text-sm text-gray-400">No projects found in database.</p>
            <p className="text-xs text-gray-600 mt-1">Use the quick creation bar above to initialize one dynamically!</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {projects.map((project) => (
              <div 
                key={project.id}
                className="bg-[#0e0c1f]/40 border border-purple-950/30 hover:border-purple-600/30 rounded-xl p-5 transition-all hover:translate-y-[-2px] hover:shadow-lg hover:shadow-purple-950/10 group flex flex-col justify-between min-h-[160px]"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <h4 className="font-semibold text-gray-200 group-hover:text-purple-400 transition-colors text-sm line-clamp-1">
                      {project.name}
                    </h4>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full border ${
                      project.status === 'Completed' 
                        ? 'bg-emerald-950/20 border-emerald-900/40 text-emerald-400'
                        : 'bg-purple-950/20 border-purple-900/40 text-purple-400'
                    }`}>
                      {project.status}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    {project.pages} pages created
                  </p>
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-purple-950/10 mt-4">
                  <span className="text-[10px] text-gray-600">Updated: {new Date(project.last_updated).toLocaleDateString()}</span>
                  <button 
                    onClick={() => onOpenProject(project.id)}
                    className="text-purple-400 hover:text-purple-300 transition-colors flex items-center gap-1 text-xs font-semibold cursor-pointer"
                  >
                    Open <ExternalLink size={12} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
