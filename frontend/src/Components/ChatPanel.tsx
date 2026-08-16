import { useEffect, useState } from 'react';
import { 
  Send, 
  Loader2, 
  MessageSquare, 
  Sparkles,
  CheckCircle2,
  Clock,
  AlertTriangle
} from 'lucide-react';

interface Project {
  id: string;
  name: string;
  pages: number;
  status: string;
  last_updated: string;
}

interface ChatPanelProps {
  projects: Project[];
  fetchProjects: () => void;
  initialProjectId?: string;
  initialMode?: 'project' | 'add_page';
  modeSignal?: number;
}

interface Message {
  sender: 'user' | 'system' | 'agent';
  agentName?: string;
  text: string;
  timestamp: Date;
}

export default function ChatPanel({
  projects,
  fetchProjects,
  initialProjectId = '',
  initialMode = 'project',
  modeSignal = 0,
}: ChatPanelProps) {
  const [selectedProjId, setSelectedProjId] = useState<string>('');
  const [prompt, setPrompt] = useState<string>('');
  const [pageName, setPageName] = useState<string>('');
  const [style, setStyle] = useState<string>('skeuomorphism');
  const [mode, setMode] = useState<'project' | 'add_page'>('project');
  const [messages, setMessages] = useState<Message[]>([]);
  const [generating, setGenerating] = useState<boolean>(false);
  
  // Pipeline steps tracking for visual progress
  const [pipelineSteps, setPipelineSteps] = useState([
    { id: 'architect', label: 'Architect Agent', status: 'idle' },
    { id: 'research', label: 'Research Agent', status: 'idle' },
    { id: 'design', label: 'Design System Agent', status: 'idle' },
    { id: 'page', label: 'Page planner', status: 'idle' },
    { id: "page_code", label: "Page Code Agent", status: "idle" },
  ]);

  useEffect(() => {
    if (initialProjectId) {
      setSelectedProjId(initialProjectId);
    }
    setMode(initialMode);

    if (initialMode === 'add_page') {
      setMessages(prev => [...prev, {
        sender: 'system',
        text: 'Add Page mode is active. Enter a page name and prompt, then generate the new page inside this project.',
        timestamp: new Date(),
      }]);
    }
  }, [initialProjectId, initialMode, modeSignal]);

  const handleSendPrompt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjId) {
      alert("Please select a project first.");
      return;
    }
    if (!prompt.trim()) return;
    if (mode === 'add_page' && !pageName.trim()) {
      alert("Please enter a page name.");
      return;
    }

    // Reset steps state
    setPipelineSteps(prev => prev.map(s => ({ ...s, status: 'idle' })));
    
    // Add user message to chat list
    const userMsg: Message = { sender: 'user', text: prompt, timestamp: new Date() };
    const systemMsg: Message = { 
      sender: 'system', 
      text: `Initializing agent team for project. Selected style: ${style}.`, 
      timestamp: new Date() 
    };
    setMessages(prev => [...prev, userMsg, systemMsg]);
    setGenerating(true);
    const userPromptText = prompt;
    const pageNameText = pageName;
    setPrompt('');

    try {
      if (mode === 'add_page') {
        setPipelineSteps(prev => prev.map((step, idx) => idx === 0 ? { ...step, status: 'running' } : { ...step, status: 'idle' }));
        const response = await fetch(`/api/projects/${selectedProjId}/add-page`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            page_name: pageNameText,
            prompt: userPromptText,
            selected_style: style,
          }),
        });

        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          throw new Error(data.detail || 'Failed to generate new page.');
        }

        setPipelineSteps(prev => prev.map(s => ({ ...s, status: 'done' })));
        setMessages(prev => [...prev, {
          sender: 'agent',
          agentName: 'Add Page Orchestrator',
          text: `New page "${pageNameText}" was generated and connected to the existing project.`,
          timestamp: new Date()
        }]);
        setPageName('');
        setGenerating(false);
        fetchProjects();
        return;
      }

      // 1. Send the initial POST request to verify/set status
      await fetch(`/api/projects/${selectedProjId}/generate-page`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: userPromptText, selected_style: style })
      });

      // 2. Open EventSource stream for real-time progress events
      const eventSource = new EventSource(
        `/api/projects/${selectedProjId}/generate-page/stream?prompt=${encodeURIComponent(userPromptText)}&style=${encodeURIComponent(style)}`
      );

      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.node === 'complete') {
          eventSource.close();
          setPipelineSteps(prev => prev.map(s => ({ ...s, status: 'done' })));
          setMessages(prev => [...prev, { 
            sender: 'agent', 
            agentName: 'System Orchestrator', 
            text: 'Website generation completed successfully! Pages and motion specifications have been compiled.', 
            timestamp: new Date() 
          }]);
          setGenerating(false);
          fetchProjects();
        } else if (data.node === 'cancelled' || data.node === 'failed') {
          eventSource.close();
          setPipelineSteps(prev => prev.map(s => s.status === 'running' || s.status === 'idle' ? { ...s, status: 'failed' } : s));
          setMessages(prev => [...prev, { 
            sender: 'system', 
            text: data.error ? `Pipeline failed: ${data.error}` : 'Generation cancelled by user.', 
            timestamp: new Date() 
          }]);
          setGenerating(false);
          fetchProjects();
        } else {
          // Event matches an agent node name (architect, research, design, page, asset, motion)
          const activeNodeId = data.node;
          
          setPipelineSteps(prev => {
            // Find current matching index
            const activeIdx = prev.findIndex(s => s.id === activeNodeId);
            if (activeIdx === -1) return prev;

            return prev.map((step, idx) => {
              if (idx < activeIdx) return { ...step, status: 'done' }; // previous is complete
              if (idx === activeIdx) return { ...step, status: 'running' }; // active
              return { ...step, status: 'idle' }; // upcoming
            });
          });

          // Print message log updates for agents
          const stepLabel = pipelineSteps.find(s => s.id === activeNodeId)?.label || activeNodeId;
          setMessages(prev => [...prev, {
            sender: 'agent',
            agentName: stepLabel,
            text: `Agent node [${activeNodeId}] has started processing...`,
            timestamp: new Date()
          }]);
        }
      };

      eventSource.onerror = (err) => {
        console.error("EventSource failed:", err);
        eventSource.close();
        setPipelineSteps(prev => prev.map(s => s.status === 'running' || s.status === 'idle' ? { ...s, status: 'failed' } : s));
        setGenerating(false);
      };

    } catch (err: any) {
      console.error(err);
      setPipelineSteps(prev => prev.map(s => s.status === 'running' || s.status === 'idle' ? { ...s, status: 'failed' } : s));
      setMessages(prev => [...prev, { 
        sender: 'system', 
        text: `Generation Failed: ${err.message || 'Unknown network error occurred.'}`, 
        timestamp: new Date() 
      }]);
      setGenerating(false);
    }
  };

  const handleCancelGeneration = async () => {
    if (!selectedProjId) return;
    try {
      const response = await fetch(`/api/projects/${selectedProjId}/cancel`, {
        method: 'POST',
      });
      if (response.ok) {
        setMessages(prev => [...prev, { 
          sender: 'system', 
          text: 'Generation pipeline was cancelled manually by the user.', 
          timestamp: new Date() 
        }]);
        setPipelineSteps(prev => prev.map(s => s.status === 'running' || s.status === 'idle' ? { ...s, status: 'failed' } : s));
      }
    } catch (error) {
      console.error('Error canceling generation:', error);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-80px)]">
      
      {/* Left Columns: Chat window */}
      <div className="lg:col-span-2 bg-[#0b0a16] border border-purple-950/20 rounded-xl flex flex-col justify-between overflow-hidden shadow-xl">
        {/* Header */}
        <div className="p-4 border-b border-purple-950/25 bg-[#0d0c20]/60 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-950/30 border border-purple-900/30 rounded-lg text-purple-400">
              <MessageSquare size={16} />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-200">
                {mode === 'add_page' ? 'Add Page Chat' : 'Agent Workspace Chat'}
              </h3>
              <p className="text-[10px] text-gray-500">
                {mode === 'add_page' ? 'Generate a new page inside the selected project' : 'Collaborate with the AI Agents pipeline'}
              </p>
            </div>
          </div>
          
          {/* Select project */}
          <div className="flex items-center gap-2">
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as 'project' | 'add_page')}
              className="bg-[#0f0e1d] border border-purple-950/40 rounded-lg px-3 py-1.5 text-xs text-gray-300 focus:outline-none focus:border-purple-600 transition-all cursor-pointer"
            >
              <option value="project">Generate Project</option>
              <option value="add_page">Generate New Page</option>
            </select>
            <select 
              value={selectedProjId}
              onChange={(e) => setSelectedProjId(e.target.value)}
              className="bg-[#0f0e1d] border border-purple-950/40 rounded-lg px-3 py-1.5 text-xs text-gray-300 focus:outline-none focus:border-purple-600 transition-all cursor-pointer"
            >
              <option value="">Select a Project...</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({p.status})</option>
              ))}
            </select>
          </div>
        </div>

        {/* Message Log */}
        <div className="flex-1 p-6 overflow-y-auto space-y-4">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center text-gray-500 max-w-sm mx-auto space-y-3">
              <Sparkles className="text-purple-500 animate-pulse" size={32} />
              <p className="text-sm font-semibold text-gray-300">Start Generating Website Assets</p>
              <p className="text-xs text-gray-500">Select a project, specify your design prompt, and click generate to invoke the agents.</p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div 
                key={idx} 
                className={`flex flex-col ${
                  msg.sender === 'user' ? 'items-end' : 'items-start'
                }`}
              >
                <div className={`max-w-md rounded-xl p-4 text-xs ${
                  msg.sender === 'user' 
                    ? 'bg-purple-600 text-white rounded-br-none shadow-md shadow-purple-950/15'
                    : msg.sender === 'system'
                    ? 'bg-purple-950/20 border border-purple-900/40 text-purple-300'
                    : 'bg-[#121024] border border-purple-950/30 text-gray-200 rounded-bl-none'
                }`}>
                  {msg.agentName && (
                    <span className="block text-[9px] font-bold uppercase tracking-wider text-purple-400 mb-1">
                      {msg.agentName}
                    </span>
                  )}
                  <p className="leading-relaxed">{msg.text}</p>
                </div>
                <span className="text-[8px] text-gray-600 mt-1">
                  {msg.timestamp.toLocaleTimeString()}
                </span>
              </div>
            ))
          )}
        </div>

        {/* Action input form */}
        <form onSubmit={handleSendPrompt} className="p-4 border-t border-purple-950/20 bg-[#0d0c20]/40 flex gap-2">
          {/* Select Style */}
          <select 
            value={style}
            onChange={(e) => setStyle(e.target.value)}
            className="bg-[#0f0e1d] border border-purple-950/40 rounded-lg px-3 py-2 text-xs text-gray-300 focus:outline-none focus:border-purple-600 cursor-pointer"
          >
            <option value="minimalism">Minimalism</option>
            <option value="glassmorphism">Glassmorphism</option>
            <option value="skeuomorphism">Skeuomorphism</option>
            <option value="neo_brutalism">Neo Brutalism</option>
            <option value="liquid_glass">Liquid Glass</option>
          </select>

          {mode === 'add_page' && (
            <input
              type="text"
              placeholder="Page name"
              disabled={!selectedProjId || generating}
              value={pageName}
              onChange={(e) => setPageName(e.target.value)}
              className="w-36 bg-[#0f0e1d] border border-purple-950/40 rounded-lg px-3 py-2 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-600 focus:ring-1 focus:ring-purple-600 transition-all disabled:opacity-50"
            />
          )}
          
          <input
            type="text"
            placeholder={
              selectedProjId
                ? mode === 'add_page'
                  ? "Describe the new page to add..."
                  : "Describe the website you want to generate..."
                : "Select a project above to start..."
            }
            disabled={!selectedProjId || generating}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="flex-1 bg-[#0f0e1d] border border-purple-950/40 rounded-lg px-4 py-2 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-600 focus:ring-1 focus:ring-purple-600 transition-all disabled:opacity-50"
          />
          {generating ? (
            <button
              type="button"
              onClick={handleCancelGeneration}
              className="bg-red-950/20 hover:bg-red-950/40 text-red-400 border border-red-900/30 rounded-lg px-4 py-2 text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5"
            >
              <Loader2 size={14} className="animate-spin" />
              Stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={!selectedProjId || !prompt.trim() || (mode === 'add_page' && !pageName.trim())}
              className="bg-purple-600 hover:bg-purple-700 text-white rounded-lg px-4 py-2 text-xs font-semibold transition-all shadow-md shadow-purple-900/10 disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
            >
              <Send size={14} />
              {mode === 'add_page' ? 'Generate New Page' : 'Generate'}
            </button>
          )}
        </form>
      </div>

      {/* Right Column: Pipeline Checklist */}
      <div className="bg-[#0b0a16] border border-purple-950/20 rounded-xl p-5 shadow-xl flex flex-col justify-between">
        <div>
          <h4 className="text-sm font-semibold text-gray-300 mb-4">Pipeline Execution State</h4>
          <div className="space-y-3">
            {pipelineSteps.map((step) => {
              const isRunning = step.status === 'running';
              const isDone = step.status === 'done';
              const isFailed = step.status === 'failed';
              return (
                <div 
                  key={step.id} 
                  className={`flex items-center justify-between p-3 border rounded-lg transition-colors ${
                    isRunning 
                      ? 'bg-purple-950/15 border-purple-600/50 text-purple-300' 
                      : isDone 
                      ? 'bg-emerald-950/10 border-emerald-900/30 text-emerald-400'
                      : isFailed
                      ? 'bg-red-950/10 border-red-900/30 text-red-400'
                      : 'bg-[#0d0c20]/40 border-purple-950/15 text-gray-500'
                  }`}
                >
                  <span className="text-xs font-semibold">{step.label}</span>
                  <div className="flex items-center gap-1.5">
                    {isRunning && <Loader2 size={12} className="animate-spin text-purple-400" />}
                    {isDone && <CheckCircle2 size={12} className="text-emerald-400" />}
                    {isFailed && <AlertTriangle size={12} className="text-red-400" />}
                    {!isRunning && !isDone && !isFailed && <Clock size={12} className="text-gray-600" />}
                    <span className="text-[9px] uppercase tracking-wider font-semibold">
                      {step.status}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        
        {/* Helper guide footer */}
        <div className="mt-6 border-t border-purple-950/15 pt-4">
          <p className="text-[10px] text-gray-500 leading-relaxed">
            The pipeline executes sequentially. Architect creates blueprints, Research analyzes references, Design establishes tokens, and Page builds section layouts.
          </p>
        </div>
      </div>

    </div>
  );
}
