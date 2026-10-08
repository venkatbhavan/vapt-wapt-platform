import { useState, useEffect } from 'react';
import { Database, Plus } from 'lucide-react';

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
      const res = await fetch('http://localhost:8000/api/projects');
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
      const res = await fetch('http://localhost:8000/api/projects', {
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
    <div className="space-y-6">
      <div className="bg-cyber-darker border border-cyber-border rounded-lg p-6">
        <h3 className="text-xl font-bold text-white mb-4">Create Project</h3>
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-cyber-text mb-1">Project Name *</label>
            <input 
              type="text" 
              value={name}
              onChange={e => setName(e.target.value)}
              className="w-full bg-cyber-darkest border border-cyber-border rounded p-2 text-white"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-cyber-text mb-1">Description</label>
            <textarea 
              value={description}
              onChange={e => setDescription(e.target.value)}
              className="w-full bg-cyber-darkest border border-cyber-border rounded p-2 text-white"
              rows={3}
            />
          </div>
          <button 
            type="submit" 
            disabled={!name || creating}
            className="flex items-center gap-2 bg-cyber-dark hover:bg-cyber-border text-cyber-accent border border-cyber-accent/50 shadow-[0_0_10px_rgba(0,240,255,0.1)] text-white font-medium py-2 px-4 rounded transition-colors disabled:opacity-50"
          >
            <Plus size={18} />
            {creating ? 'Creating...' : 'Create Project'}
          </button>
        </form>
        {error && <p className="text-red-500 mt-4 text-sm">{error}</p>}
      </div>

      <div className="bg-cyber-darker border border-cyber-border rounded-lg p-6">
        <h3 className="text-xl font-bold text-white mb-4">Projects</h3>
        {loading ? (
          <p className="text-cyber-text">Loading projects...</p>
        ) : projects.length === 0 ? (
          <p className="text-cyber-text">No projects found. Create one above.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map(p => (
              <div 
                key={p.id} 
                className="bg-cyber-darkest border border-cyber-border p-4 rounded-lg cursor-pointer hover:border-cyber-accent transition-colors"
                onClick={() => onSelectProject(p.id)}
              >
                <div className="flex items-start justify-between mb-2">
                  <h4 className="text-lg font-bold text-white truncate pr-2">{p.name}</h4>
                  <Database size={16} className="text-cyber-text flex-shrink-0 mt-1" />
                </div>
                <p className="text-sm text-cyber-text mb-4 line-clamp-2">{p.description || 'No description'}</p>
                <p className="text-xs text-cyber-border">ID: {p.id}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
