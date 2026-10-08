import { useState, useEffect } from 'react';
import { Database, Plus, Terminal, Shield, FolderGit2, AlertTriangle, ArrowRight } from 'lucide-react';

interface Project {
  id: number;
  name: string;
  description: string;
}

interface ProjectsViewProps {
  onSelectProject: (id: number) => void;
}

export function ProjectsView({ onSelectProject }: ProjectsViewProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [creating, setCreating] = useState(false);

  const fetchProjects = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/projects`);
      if (!res.ok) throw new Error('Failed to fetch projects');
      const data = await res.json();
      setProjects(data);
    } catch (err: any) {
      setError(err.message || 'API unavailable');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name) return;
    setCreating(true);
    setError('');
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to create project');
      }
      setName('');
      setDescription('');
      await fetchProjects();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Create Project Panel */}
      <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
        <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
          <Terminal size={18} className="text-cyber-accent" />
          <h3 className="font-mono text-white tracking-widest uppercase text-sm">Initialize Security Project</h3>
        </div>
        
        <div className="p-6">
          <form onSubmit={handleCreate} className="space-y-6 max-w-3xl">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-1">
                <label className="flex items-center gap-2 text-xs font-mono text-cyber-accent uppercase tracking-wider mb-2">
                  Project Identifier
                </label>
                <input 
                  type="text" 
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="e.g. PRJ-INTERNAL-01"
                  className="w-full bg-cyber-darkest border border-cyber-border focus:border-cyber-accent rounded p-2.5 text-white font-mono text-sm transition-colors focus:outline-none focus:ring-1 focus:ring-cyber-accent"
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="flex items-center gap-2 text-xs font-mono text-cyber-accent uppercase tracking-wider mb-2">
                  Scope Description
                </label>
                <input 
                  type="text" 
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  placeholder="Project scope boundary..."
                  className="w-full bg-cyber-darkest border border-cyber-border focus:border-cyber-accent rounded p-2.5 text-white font-mono text-sm transition-colors focus:outline-none focus:ring-1 focus:ring-cyber-accent"
                />
              </div>
            </div>
            
            <div className="pt-2">
              <button 
                type="submit" 
                disabled={!name || creating}
                className="flex items-center gap-2 bg-cyber-accent hover:bg-cyber-accent/80 text-black font-bold uppercase tracking-widest py-2.5 px-6 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
              >
                <Plus size={16} />
                {creating ? 'Initializing...' : 'Create Workspace'}
              </button>
            </div>
          </form>
          {error && (
            <div className="mt-4 bg-red-900/20 border border-red-500/50 text-red-500 p-3 rounded flex items-center gap-2 text-sm font-mono">
              <AlertTriangle size={16} />
              {error}
            </div>
          )}
        </div>
      </div>

      {/* Projects Grid */}
      <div className="space-y-4">
        <h3 className="font-mono text-white tracking-widest uppercase text-sm flex items-center gap-2">
          <FolderGit2 size={16} className="text-cyber-accent" /> Active Workspaces
        </h3>
        
        {loading ? (
          <div className="p-8 text-center text-cyber-accent font-mono animate-pulse border border-cyber-border rounded bg-cyber-darker">
            SCANNING FOR WORKSPACES...
          </div>
        ) : projects.length === 0 ? (
          <div className="border border-cyber-border bg-cyber-darker p-10 rounded text-center flex flex-col items-center justify-center">
            <Database size={48} className="text-cyber-border mb-4" />
            <h4 className="text-white font-mono uppercase tracking-widest mb-2">No Workspaces Detected</h4>
            <p className="text-cyber-text text-sm font-mono uppercase">Initialize a new security project to begin operations.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map(p => (
              <div 
                key={p.id} 
                onClick={() => onSelectProject(p.id)}
                className="group bg-cyber-darker border border-cyber-border hover:border-cyber-accent rounded p-5 cursor-pointer transition-all hover:shadow-[0_0_15px_rgba(0,255,255,0.15)] relative overflow-hidden flex flex-col min-h-[160px]"
              >
                <div className="absolute top-0 left-0 w-1 h-full bg-cyber-border group-hover:bg-cyber-accent transition-colors"></div>
                
                <div className="flex justify-between items-start mb-3 ml-2">
                  <h4 className="text-white font-bold font-mono tracking-wide text-lg truncate pr-4">{p.name}</h4>
                  <Shield size={18} className="text-cyber-accent/70 group-hover:text-cyber-accent transition-colors flex-shrink-0" />
                </div>
                
                <p className="text-cyber-text text-sm mb-auto ml-2 line-clamp-2">{p.description || 'No scope defined.'}</p>
                
                <div className="mt-4 pt-4 border-t border-cyber-border/50 flex justify-between items-center ml-2">
                  <span className="text-xs font-mono text-cyber-text/70 uppercase">ID: {String(p.id).padStart(4, '0')}</span>
                  <span className="text-xs font-mono text-cyber-accent flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    ACCESS CONSOLE <ArrowRight size={14} />
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
