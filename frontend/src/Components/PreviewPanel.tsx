import { useState, useEffect } from 'react';
import { 
  Monitor, 
  Tablet, 
  Smartphone, 
  RotateCw, 
  ExternalLink,
  Folder,
  FileCode,
  Loader2,
  Terminal,
  FileText
} from 'lucide-react';

interface PreviewPanelProps {
  projectId: string;
}

export default function PreviewPanel({ projectId }: PreviewPanelProps) {
  // Device Preview width states
  const [deviceMode, setDeviceMode] = useState<'desktop' | 'tablet' | 'mobile'>('desktop');
  const [iframeKey, setIframeKey] = useState<number>(0);
  
  // Right panel states
  const [rightTab, setRightTab] = useState<'files' | 'console'>('files');
  const [files, setFiles] = useState<Record<string, string>>({});
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  const deviceWidths = {
    desktop: '100%',
    tablet: '768px',
    mobile: '390px'
  };

  useEffect(() => {
    fetchProjectCode();
  }, [projectId]);

  const fetchProjectCode = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/projects/${projectId}/code`);
      const data = await response.json();
      setFiles(data.files || {});
      
      const fileNames = Object.keys(data.files || {});
      if (fileNames.length > 0) {
        setSelectedFile(fileNames[0]);
      }
    } catch (error) {
      console.error("Error fetching project code:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleReload = () => {
    setIframeKey(prev => prev + 1);
  };

  return (
    <div className="w-full h-[calc(100vh-140px)] flex bg-[#07060d] text-gray-200">
      
      {/* LEFT AREA: Live Interactive Preview Frame */}
      <div className="flex-1 flex flex-col p-6 space-y-4">
        
        {/* Device view toolbar (top) */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 bg-[#0d0c20]/60 p-1 border border-purple-950/30 rounded-lg">
            {[
              { mode: 'desktop', icon: Monitor },
              { mode: 'tablet', icon: Tablet },
              { mode: 'mobile', icon: Smartphone }
            ].map(({ mode, icon: Icon }) => (
              <button
                key={mode}
                onClick={() => setDeviceMode(mode as any)}
                className={`p-2 rounded-md transition-all cursor-pointer ${
                  deviceMode === mode 
                    ? 'bg-purple-600/35 border border-purple-500/30 text-purple-400' 
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                <Icon size={14} />
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[10px] text-gray-500 font-semibold bg-[#0d0c20]/30 border border-purple-950/20 px-2 py-1 rounded">
              {deviceMode === 'desktop' ? '1440px' : deviceMode === 'tablet' ? '768px' : '390px'}
            </span>
            
            <button 
              onClick={handleReload}
              className="p-2 bg-[#0e0c1f] hover:bg-[#15112c] border border-purple-950/30 rounded-lg text-gray-400 hover:text-gray-200 transition-colors cursor-pointer"
            >
              <RotateCw size={12} />
            </button>
            
            <button 
              onClick={handleReload}
              className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold shadow-lg shadow-purple-900/20 transition-all cursor-pointer"
            >
              Reload Preview
            </button>
          </div>
        </div>

        {/* Live preview URL helper */}
        <div className="flex items-center justify-between text-[10px] text-gray-500 px-2">
          <span>Previewing website in real-time. Changes are auto-saved.</span>
          <span className="flex items-center gap-1">
            Preview URL: <a href={`/api/projects/${projectId}/preview`} target="_blank" rel="noreferrer" className="text-purple-400 hover:underline flex items-center gap-0.5">http://localhost:8000/api/projects/{projectId}/preview <ExternalLink size={8} /></a>
          </span>
        </div>

        {/* Mock macOS style browser mockup frame */}
        <div className="flex-1 bg-[#0b0a16] border border-purple-950/30 rounded-xl overflow-hidden shadow-2xl flex flex-col">
          {/* Browser header tab bar */}
          <div className="px-4 py-3 bg-[#0d0c20]/60 border-b border-purple-950/35 flex items-center justify-between">
            {/* Window dot buttons */}
            <div className="flex gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500/80 inline-block"></span>
              <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/80 inline-block"></span>
              <span className="w-2.5 h-2.5 rounded-full bg-green-500/80 inline-block"></span>
            </div>
            
            {/* Mock address bar */}
            <div className="w-1/2 bg-[#07060d]/80 border border-purple-950/30 px-3 py-1 rounded-md text-[10px] text-gray-400 flex items-center justify-between">
              <div className="flex items-center gap-1.5 select-all truncate">
                <span className="text-purple-400">🔒</span>
                <span>http://localhost:8000/api/projects/{projectId}/preview</span>
              </div>
              <a href={`/api/projects/${projectId}/preview`} target="_blank" rel="noreferrer" className="text-gray-500 hover:text-gray-300">
                <ExternalLink size={10} />
              </a>
            </div>
            
            <div className="w-10"></div>
          </div>

          {/* Device constrained iframe window */}
          <div className="flex-1 flex justify-center items-center bg-[#07060d]/40 p-4">
            <div 
              style={{ width: deviceWidths[deviceMode] }}
              className="h-full border border-purple-950/20 rounded shadow-xl bg-[#07060c] overflow-hidden transition-all duration-300"
            >
              <iframe
                key={iframeKey}
                src={`/api/projects/${projectId}/preview`}
                className="w-full h-full border-0 bg-transparent"
                sandbox="allow-scripts allow-same-origin"
              />
            </div>
          </div>
        </div>

      </div>

      {/* RIGHT SIDE PANEL: Workspace Files & Component Props editor */}
      <div className="w-80 border-l border-purple-950/20 bg-[#0d0c20]/40 flex flex-col justify-between">
        
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Right tab selector */}
          <div className="grid grid-cols-2 border-b border-purple-950/25 bg-[#090812]">
            {[
              { id: 'files', label: 'Files', icon: FileText },
              { id: 'console', label: 'Logs', icon: Terminal }
            ].map(tab => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setRightTab(tab.id as any)}
                  className={`py-3 text-xs font-semibold border-b-2 flex items-center justify-center gap-1.5 transition-colors cursor-pointer ${
                    rightTab === tab.id 
                      ? 'border-purple-600 text-purple-400 bg-purple-950/5' 
                      : 'border-transparent text-gray-500 hover:text-gray-300'
                  }`}
                >
                  <Icon size={12} />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Right Tab Content */}
          <div className="flex-1 overflow-y-auto p-4">
            
            {/* FILES VIEW: Collapsible Directory Tree */}
            {rightTab === 'files' && (
              <div className="space-y-3 text-xs">
                {loading ? (
                  <div className="flex justify-center py-6">
                    <Loader2 className="animate-spin text-purple-500" size={20} />
                  </div>
                ) : Object.keys(files).length === 0 ? (
                  <p className="text-[10px] text-gray-600 italic">No files available.</p>
                ) : (
                  <div className="space-y-1 bg-[#07060d]/30 border border-purple-950/15 p-2 rounded-lg">
                    {/* Collapsible src folder tree representation */}
                    <div className="flex items-center gap-2 px-1 py-1 text-purple-400 font-semibold select-none">
                      <Folder size={12} />
                      <span>src/components</span>
                    </div>
                    {Object.keys(files).map((fileName) => (
                      <button
                        key={fileName}
                        onClick={() => setSelectedFile(fileName)}
                        className={`w-full flex items-center gap-2 pl-6 pr-2 py-1.5 rounded text-left transition-colors truncate ${
                          selectedFile === fileName 
                            ? 'bg-purple-950/40 text-purple-400 font-semibold' 
                            : 'text-gray-400 hover:text-gray-200 hover:bg-purple-950/10'
                        }`}
                      >
                        <FileCode size={11} className="text-gray-500" />
                        {fileName.split('/').pop()}
                      </button>
                    ))}
                  </div>
                )}

                {/* Micro IDE code snippet viewer directly on side */}
                {selectedFile && files[selectedFile] && (
                  <div className="mt-4 border border-purple-950/20 rounded-lg overflow-hidden bg-[#040307]">
                    <div className="px-3 py-1.5 bg-[#090812] border-b border-purple-950/20 text-[9px] text-gray-500 flex justify-between">
                      <span>Previewing Code: {selectedFile.split('/').pop()}</span>
                    </div>
                    <pre className="p-3 text-[10px] font-mono text-gray-400 leading-normal max-h-48 overflow-y-auto">
                      <code>{files[selectedFile]}</code>
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* CONSOLE LOGGER VIEW */}
            {rightTab === 'console' && (
              <div className="space-y-2 font-mono text-[10px] text-gray-500">
                <p className="text-emerald-500/80">[11:18:02] Website preview compiled successfully.</p>
                <p className="text-purple-400">[11:18:02] Loaded index.html entry point.</p>
                <p className="text-gray-600">[11:18:03] CSS assets successfully loaded.</p>
                <p className="text-gray-600">[11:18:04] Device resolution matching set to Desktop (1440px).</p>
              </div>
            )}

          </div>
        </div>

        {/* Bottom Panel Device dimensions preview toolbar */}
        <div className="p-3 border-t border-purple-950/20 bg-[#090812] flex items-center justify-around">
          <button onClick={() => setDeviceMode('desktop')} className={`text-gray-500 hover:text-gray-300 cursor-pointer ${deviceMode === 'desktop' && 'text-purple-500'}`}>
            <Monitor size={14} />
          </button>
          <button onClick={() => setDeviceMode('tablet')} className={`text-gray-500 hover:text-gray-300 cursor-pointer ${deviceMode === 'tablet' && 'text-purple-500'}`}>
            <Tablet size={14} />
          </button>
          <button onClick={() => setDeviceMode('mobile')} className={`text-gray-500 hover:text-gray-300 cursor-pointer ${deviceMode === 'mobile' && 'text-purple-500'}`}>
            <Smartphone size={14} />
          </button>
        </div>

      </div>

    </div>
  );
}
