import { 
  LayoutDashboard, 
  FolderKanban, 
  MessageSquare, 
  Image as ImageIcon, 
  Settings, 
  Layers 
} from 'lucide-react';

interface SidebarProps {
  activeTab: 'dashboard' | 'projects' | 'chats' | 'assets' | 'settings';
  setActiveTab: (tab: 'dashboard' | 'projects' | 'chats' | 'assets' | 'settings') => void;
}

export default function Sidebar({ activeTab, setActiveTab }: SidebarProps) {
  return (
    <aside className="w-64 bg-[#0d0b18] border-r border-purple-950/30 flex flex-col justify-between p-4 h-screen sticky top-0">
      <div>
        {/* Logo Brand */}
        <div className="flex items-center gap-3 px-2 py-4 mb-6">
          <div className="p-2 bg-purple-900/30 border border-purple-500/30 rounded-lg text-purple-400">
            <Layers size={20} />
          </div>
          <div>
            <h1 className="text-md font-bold tracking-wide bg-gradient-to-r from-purple-400 to-indigo-400 bg-clip-text text-transparent">
              AI Builder
            </h1>
            <p className="text-[10px] text-gray-500 font-medium">Idea to Production</p>
          </div>
        </div>

        {/* Nav Items */}
        <nav className="space-y-1.5">
          {[
            { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
            { id: 'projects', label: 'Projects', icon: FolderKanban },
            { id: 'chats', label: 'Chats', icon: MessageSquare },
            { id: 'assets', label: 'Assets', icon: ImageIcon },
            { id: 'settings', label: 'Settings', icon: Settings },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive 
                    ? 'bg-purple-950/40 text-purple-400 border border-purple-900/40 shadow-lg shadow-purple-950/20' 
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-900/20 border border-transparent'
                }`}
              >
                <Icon size={16} />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* User Profile */}
      <div className="border-t border-purple-950/20 pt-4 flex items-center gap-3 px-2">
        <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-purple-600 to-indigo-600 flex items-center justify-center text-xs font-semibold text-white shadow-md">
          JD
        </div>
        <div>
          <p className="text-xs font-semibold text-gray-200">John Doe</p>
          <p className="text-[10px] text-gray-500">Developer</p>
        </div>
      </div>
    </aside>
  );
}
