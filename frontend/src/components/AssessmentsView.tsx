import { useState, useEffect } from 'react';
import { ShieldAlert, ArrowLeft, Plus, Activity } from 'lucide-react';

interface Assessment {
  id: number;
  project_id: number;
  name: string;
  target: string;
  scope: string;
  authorization_confirmed: boolean;
  scan_profile: string;
  status: string;
  created_at: string;
}

interface AssessmentsViewProps {
  projectId: number;
  onBack: () => void;
  onSelectAssessment: (assessmentId: number) => void;
}

export function AssessmentsView({ projectId, onBack, onSelectAssessment }: AssessmentsViewProps) {
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Form State
  const [name, setName] = useState('');
  const [target, setTarget] = useState('');
  const [scope, setScope] = useState('');
  const [scanProfile, setScanProfile] = useState('passive');
  const [authConfirmed, setAuthConfirmed] = useState(false);
  const [creating, setCreating] = useState(false);

  const fetchAssessments = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}`}/api/projects/${projectId}/assessments`);
      if (res.status === 404) {
        throw new Error('Project not found');
      }
      if (!res.ok) throw new Error('Failed to fetch assessments');
      const data = await res.json();
      setAssessments(data);
    } catch (err: any) {
      setError(err.message || 'API unavailable');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssessments();
  }, [projectId]);

  const isValid = name.trim() !== '' && target.trim() !== '' && scope.trim() !== '' && authConfirmed;

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid) return;
    
    setCreating(true);
    setError('');
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}`}/api/projects/${projectId}/assessments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          target,
          scope,
          scan_profile: scanProfile,
          authorization_confirmed: authConfirmed,
        }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to create assessment');
      }
      
      // Reset form
      setName('');
      setTarget('');
      setScope('');
      setScanProfile('passive');
      setAuthConfirmed(false);
      
      await fetchAssessments();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      <button 
        onClick={onBack}
        className="flex items-center gap-2 text-cyber-text hover:text-white transition-colors"
      >
        <ArrowLeft size={16} /> Back to Projects
      </button>

      {error && (
        <div className="bg-red-500/10 border border-red-500 text-red-500 p-4 rounded-lg flex items-center gap-3">
          <ShieldAlert size={20} />
          <p>{error}</p>
        </div>
      )}

      <div className="bg-cyber-darker border border-cyber-border rounded-lg p-6">
        <h3 className="text-xl font-bold text-white mb-4">Create Assessment</h3>
        <form onSubmit={handleCreate} className="space-y-4 max-w-2xl">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-cyber-text mb-1">Assessment Name *</label>
              <input 
                type="text" 
                value={name}
                onChange={e => setName(e.target.value)}
                className="w-full bg-cyber-darkest border border-cyber-border rounded p-2 text-white"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-cyber-text mb-1">Target *</label>
              <input 
                type="text" 
                value={target}
                onChange={e => setTarget(e.target.value)}
                placeholder="e.g. https://example.com"
                className="w-full bg-cyber-darkest border border-cyber-border rounded p-2 text-white"
                required
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-cyber-text mb-1">Scope *</label>
            <textarea 
              value={scope}
              onChange={e => setScope(e.target.value)}
              placeholder="Define the testing scope..."
              className="w-full bg-cyber-darkest border border-cyber-border rounded p-2 text-white"
              rows={3}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-cyber-text mb-1">Scan Profile</label>
            <select 
              value={scanProfile}
              onChange={e => setScanProfile(e.target.value)}
              className="w-full bg-cyber-darkest border border-cyber-border rounded p-2 text-white"
            >
              <option value="passive">Passive</option>
              <option value="safe">Safe</option>
              <option value="standard">Standard</option>
              <option value="active">Active</option>
              <option value="deep">Deep</option>
            </select>
          </div>

          <div className="bg-cyber-darkest border border-red-900/50 rounded p-4 mt-6">
            <label className="flex items-start gap-3 cursor-pointer">
              <input 
                type="checkbox" 
                checked={authConfirmed}
                onChange={e => setAuthConfirmed(e.target.checked)}
                className="mt-1 w-4 h-4 text-cyber-accent rounded bg-cyber-darker border-cyber-border focus:ring-cyber-accent focus:ring-offset-gray-900"
              />
              <span className="text-sm text-cyber-textBright">
                <strong className="block text-white mb-1">Authorization Required</strong>
                I confirm that I am authorized to perform security testing against this target and that the target is within the stated scope.
              </span>
            </label>
          </div>

          <button 
            type="submit" 
            disabled={!isValid || creating}
            className="flex items-center gap-2 bg-cyber-dark hover:bg-cyber-border text-cyber-accent border border-cyber-accent/50 shadow-[0_0_10px_rgba(0,240,255,0.1)] text-white font-medium py-2 px-6 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-4"
          >
            <Plus size={18} />
            {creating ? 'Creating...' : 'Create Assessment'}
          </button>
        </form>
      </div>

      <div className="bg-cyber-darker border border-cyber-border rounded-lg p-6">
        <h3 className="text-xl font-bold text-white mb-4">Project Assessments</h3>
        {loading ? (
          <p className="text-cyber-text">Loading assessments...</p>
        ) : assessments.length === 0 ? (
          <p className="text-cyber-text">No assessments found for this project.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-cyber-border text-cyber-text text-sm">
                  <th className="pb-3 pr-4 font-medium">Name</th>
                  <th className="pb-3 pr-4 font-medium">Target</th>
                  <th className="pb-3 pr-4 font-medium">Profile</th>
                  <th className="pb-3 pr-4 font-medium">Status</th>
                  <th className="pb-3 pr-4 font-medium">Auth</th>
                  <th className="pb-3 pr-4 font-medium">Created</th>
                  <th className="pb-3"></th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {assessments.map(a => (
                  <tr key={a.id} className="border-b border-cyber-border/50 hover:bg-cyber-dark/20">
                    <td className="py-3 pr-4 font-medium text-white">{a.name}</td>
                    <td className="py-3 pr-4 text-cyber-accent">{a.target}</td>
                    <td className="py-3 pr-4">
                      <span className="bg-cyber-dark text-cyber-textBright px-2 py-1 rounded text-xs uppercase tracking-wider">
                        {a.scan_profile}
                      </span>
                    </td>
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-1.5">
                        <Activity size={14} className="text-cyber-text" />
                        <span className="capitalize text-cyber-textBright">{a.status}</span>
                      </div>
                    </td>
                    <td className="py-3 pr-4">
                      {a.authorization_confirmed ? (
                        <span className="text-green-500 text-xs border border-green-500/20 bg-green-500/10 px-2 py-1 rounded">Confirmed</span>
                      ) : (
                        <span className="text-red-500 text-xs">Missing</span>
                      )}
                    </td>
                    <td className="py-3 pr-4 text-cyber-text">
                      {new Date(a.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => onSelectAssessment(a.id)}
                        className="text-cyber-accent hover:text-cyber-accent text-sm font-medium px-3 py-1 bg-cyber-accent/10 hover:bg-cyber-accent/20 rounded transition-colors"
                      >
                        View Dashboard
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
