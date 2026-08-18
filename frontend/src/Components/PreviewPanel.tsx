import { useEffect, useState } from 'react';
import {
  Code2,
  ExternalLink,
  Loader2,
  Monitor,
  Play,
  RefreshCw,
  Sparkles,
} from 'lucide-react';

interface PreviewPanelProps {
  projectId: string;
  pageName?: string;
  pageRoute?: string;
  pageFilePath?: string;
  onGenerateAssets: () => void;
}

type BuildState = 'idle' | 'running' | 'ready' | 'error';

export default function PreviewPanel({ projectId, pageName, pageRoute, pageFilePath, onGenerateAssets }: PreviewPanelProps) {
  const [buildState, setBuildState] = useState<BuildState>('idle');
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [buildLog, setBuildLog] = useState<string>('Preview server has not been started yet.');
  const [codeFiles, setCodeFiles] = useState<Record<string, string>>({});
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [generatingAssets, setGeneratingAssets] = useState(false);

  const fetchCode = async () => {
    try {
      const response = await fetch(`/api/projects/${projectId}/code`);
      const data = await response.json();
      const files = data.files || {};
      setCodeFiles(files);
      setSelectedFile(prev => {
        if (pageFilePath && files[pageFilePath]) return pageFilePath;
        return prev || Object.keys(files)[0] || '';
      });
    } catch (error) {
      console.error('Failed to load generated code:', error);
    }
  };

  const checkPreviewStatus = async () => {
    try {
      const params = pageName ? `?page_name=${encodeURIComponent(pageName)}` : '';
      const response = await fetch(`/api/projects/${projectId}/preview-status${params}`);
      const data = await response.json();
      if (data.running && data.preview_url) {
        setPreviewUrl(data.preview_url);
        setBuildState('ready');
        setBuildLog('Preview server is already running.');
      }
    } catch (error) {
      console.error('Failed to check preview status:', error);
    }
  };

  useEffect(() => {
    fetchCode();
    checkPreviewStatus();
  }, [projectId, pageName]);

  const startPreview = async () => {
    try {
      setBuildState('running');
      setBuildLog('Checking build and starting preview server...');
      const params = pageName ? `?page_name=${encodeURIComponent(pageName)}` : '';
      const response = await fetch(`/api/projects/${projectId}/build${params}`, {
        method: 'POST',
      });

      if (!response.ok || !response.body) {
        throw new Error('Preview build request failed.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';

        for (const event of events) {
          const line = event.split('\n').find(item => item.startsWith('data: '));
          if (!line) continue;

          const data = JSON.parse(line.replace('data: ', ''));

          if (data.step === 'build_check' && data.status === 'running') {
            setBuildLog(data.msg || 'Checking build...');
          } else if (data.step === 'repair' && data.status === 'running') {
            setBuildLog(data.msg || `Repair attempt ${data.attempt || ''}...`.trim());
          } else if (data.step === 'dev_server' && data.status === 'running') {
            setBuildLog(data.msg || 'Starting dev server...');
          } else if (data.msg) {
            setBuildLog(data.msg);
          }

          if (data.status === 'error') {
            setBuildState('error');
            setBuildLog(data.msg || 'Preview build failed.');
          }

          if (data.status === 'done') {
            setBuildState('ready');
            setPreviewUrl(data.preview_url);
            setBuildLog('Preview is ready.');
            fetchCode();
          }
        }
      }
    } catch (error: any) {
      console.error('Failed to start preview:', error);
      setBuildState('error');
      setBuildLog(error?.message || 'Preview build failed.');
    }
  };

  const generateAssets = async () => {
    try {
      setGeneratingAssets(true);
      const params = pageName ? `?page_name=${encodeURIComponent(pageName)}` : '';
      const response = await fetch(`/api/projects/${projectId}/generate-assets${params}`, {
        method: 'POST',
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'Asset generation failed.');
      }

      onGenerateAssets();
    } catch (error: any) {
      console.error('Failed to generate assets:', error);
      alert(error?.message || 'Asset generation failed.');
    } finally {
      setGeneratingAssets(false);
    }
  };

  const fileNames = Object.keys(codeFiles);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-5 gap-5">
      <section className="xl:col-span-3 bg-[#0b0a16] border border-purple-950/20 rounded-xl overflow-hidden shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-4 py-3 border-b border-purple-950/20 bg-[#0d0c20]/50">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-purple-950/25 border border-purple-900/30 rounded-lg text-purple-400">
              <Monitor size={15} />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-200">Website Preview</h3>
              <p className="text-[10px] text-gray-500">
                {pageName ? `${pageName}${pageRoute ? ` - ${pageRoute}` : ''}` : 'Current project'} - {buildLog}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {previewUrl && (
              <a
                href={previewUrl}
                target="_blank"
                rel="noreferrer"
                className="p-2 bg-[#0e0c1f] hover:bg-[#15112c] border border-purple-950/30 rounded-lg text-gray-400 hover:text-gray-200"
                title="Open preview"
              >
                <ExternalLink size={14} />
              </a>
            )}
            <button
              type="button"
              onClick={startPreview}
              disabled={buildState === 'running'}
              className="flex items-center gap-1.5 px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold shadow-lg shadow-purple-900/20 disabled:opacity-60 cursor-pointer"
            >
              {buildState === 'running' ? <Loader2 size={13} className="animate-spin" /> : buildState === 'ready' ? <RefreshCw size={13} /> : <Play size={13} />}
              {buildState === 'ready' ? 'Restart' : 'Start'}
            </button>
          </div>
        </div>

        <div className="h-[560px] bg-[#07060d]">
          {previewUrl && buildState === 'ready' ? (
            <iframe
              src={previewUrl}
              title="Generated website preview"
              className="w-full h-full bg-white"
            />
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center px-6">
              <Monitor className="text-purple-500 mb-3" size={34} />
              <p className="text-sm font-semibold text-gray-300">Preview server is offline</p>
              <p className="text-xs text-gray-500 mt-1 max-w-sm">
                Start the generated Vite site to inspect the compiled website here.
              </p>
            </div>
          )}
        </div>
      </section>

      <aside className="xl:col-span-2 space-y-5">
        <section className="bg-[#0b0a16] border border-purple-950/20 rounded-xl p-4 shadow-xl">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Code2 size={15} className="text-purple-400" />
              <h3 className="text-sm font-semibold text-gray-200">Generated Code</h3>
            </div>
            <button
              type="button"
              onClick={fetchCode}
              className="p-1.5 bg-[#0e0c1f] hover:bg-[#15112c] border border-purple-950/30 rounded text-gray-400"
              title="Refresh code"
            >
              <RefreshCw size={12} />
            </button>
          </div>

          <select
            value={selectedFile}
            onChange={(event) => setSelectedFile(event.target.value)}
            className="w-full bg-[#07060d] border border-purple-950/35 rounded-lg px-3 py-2 text-xs text-gray-300 focus:outline-none focus:border-purple-600"
          >
            {fileNames.length === 0 ? (
              <option value="">No files found</option>
            ) : (
              fileNames.map(fileName => (
                <option key={fileName} value={fileName}>{fileName}</option>
              ))
            )}
          </select>

          <pre className="mt-3 h-[360px] overflow-auto rounded-lg bg-[#07060d] border border-purple-950/25 p-3 text-[10px] leading-relaxed text-gray-300">
            <code>{selectedFile ? codeFiles[selectedFile] : 'No generated code available.'}</code>
          </pre>
        </section>

        <section className="bg-[#0b0a16] border border-purple-950/20 rounded-xl p-4 shadow-xl">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles size={15} className="text-purple-400" />
            <h3 className="text-sm font-semibold text-gray-200">Assets</h3>
          </div>
          <p className="text-xs text-gray-500 leading-relaxed mb-4">
            Generate the image assets planned for {pageName || 'this project'}, then review or replace them in Asset Studio.
          </p>
          <button
            type="button"
            onClick={generateAssets}
            disabled={generatingAssets}
            className="w-full flex items-center justify-center gap-1.5 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold shadow-lg shadow-purple-900/20 disabled:opacity-60 cursor-pointer"
          >
            {generatingAssets ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
            Generate Assets
          </button>
        </section>
      </aside>
    </div>
  );
}
