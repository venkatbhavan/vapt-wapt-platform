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
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <h3 className="text-xl font-bold text-white mb-4">Create Project</h3>
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Project Name *</label>
            <input 
              type="text" 
              value={name}
              onChange={e => setName(e.target.value)}
              className="w-full bg-gray-950 border border-gray-700 rounded p-2 text-white"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Description</label>
            <textarea 
              value={description}
              onChange={e => setDescription(e.target.value)}
              className="w-full bg-gray-950 border border-gray-700 rounded p-2 text-white"
              rows={3}
            />
          </div>
          <button 
            type="submit" 
            disabled={!name || creating}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded transition-colors disabled:opacity-50"
          >
            <Plus size={18} />
            {creating ? 'Creating...' : 'Create Project'}
          </button>
        </form>
        {error && <p className="text-red-500 mt-4 text-sm">{error}</p>}
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <h3 className="text-xl font-bold text-white mb-4">Projects</h3>
        {loading ? (
          <p className="text-gray-400">Loading projects...</p>
        ) : projects.length === 0 ? (
          <p className="text-gray-400">No projects found. Create one above.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map(p => (
              <div 
                key={p.id} 
                className="bg-gray-950 border border-gray-800 p-4 rounded-lg cursor-pointer hover:border-blue-500 transition-colors"
                onClick={() => onSelectProject(p.id)}
              >
                <div className="flex items-start justify-between mb-2">
                  <h4 className="text-lg font-bold text-white truncate pr-2">{p.name}</h4>
                  <Database size={16} className="text-gray-500 flex-shrink-0 mt-1" />
                </div>
                <p className="text-sm text-gray-400 mb-4 line-clamp-2">{p.description || 'No description'}</p>
                <p className="text-xs text-gray-600">ID: {p.id}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
