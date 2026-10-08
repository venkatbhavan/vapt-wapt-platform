import { useState, useEffect } from 'react';
import { ArrowLeft, ShieldAlert, Activity, Crosshair, Radar, ShieldCheck, Database, Target, Map } from 'lucide-react';

interface Assessment {
  id: number;
  name: string;
  target: string;
  status: string;
  scan_profile: string;
  authorization_confirmed: boolean;
  created_at: string;
}

interface AssessmentsViewProps {
  projectId: number;
  onSelectAssessment: (id: number) => void;
  onBack: () => void;
}

export function AssessmentsView({ projectId, onSelectAssessment, onBack }: AssessmentsViewProps) {
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const [name, setName] = useState('');
  const [target, setTarget] = useState('');
  const [scope, setScope] = useState('');
  const [scanProfile, setScanProfile] = useState('passive');
  const [authConfirmed, setAuthConfirmed] = useState(false);
  const [creating, setCreating] = useState(false);

  const isValid = name && target && scope && authConfirmed;

  const fetchAssessments = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/projects/${projectId}/assessments`);
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

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid) return;
    
    setCreating(true);
    setError('');
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/projects/${projectId}/assessments`, {
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
        className="flex items-center gap-2 text-cyber-text hover:text-cyber-accent transition-colors font-mono text-sm uppercase tracking-wider"
      >
        <ArrowLeft size={16} /> RETURN TO WORKSPACES
      </button>

      {error && (
        <div className="bg-red-900/20 border border-red-500/50 text-red-500 p-4 rounded flex items-center gap-3 font-mono text-sm">
          <ShieldAlert size={18} />
          <p>{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Creation Panel */}
        <div className="xl:col-span-1 bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden h-fit">
          <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
            <Radar size={18} className="text-cyber-accent" />
            <h3 className="font-mono text-white tracking-widest uppercase text-sm">Initialize Security Assessment</h3>
          </div>
          
          <form onSubmit={handleCreate} className="p-5 space-y-6">
            {/* Identity */}
            <div className="space-y-4">
              <h4 className="text-xs font-mono text-cyber-accent/70 uppercase tracking-widest border-b border-cyber-border/50 pb-1 mb-3 flex items-center gap-2">
                <Target size={14} /> Assessment Identity
              </h4>
              
              <div>
                <label className="block text-xs font-mono text-cyber-text mb-1 uppercase tracking-wider">Assessment Name</label>
                <input 
                  type="text" 
                  value={name}
                  onChange={e => setName(e.target.value)}
                  className="w-full bg-cyber-darkest border border-cyber-border focus:border-cyber-accent rounded p-2 text-white font-mono text-sm focus:outline-none transition-colors"
                  placeholder="e.g. Q4 Web Core Scan"
                  required
                />
              </div>
              
              <div>
                <label className="block text-xs font-mono text-cyber-text mb-1 uppercase tracking-wider">Primary Target</label>
                <input 
                  type="text" 
                  value={target}
                  onChange={e => setTarget(e.target.value)}
                  placeholder="IP or domain (e.g. 10.0.0.1)"
                  className="w-full bg-cyber-darkest border border-cyber-border focus:border-cyber-accent rounded p-2 text-white font-mono text-sm focus:outline-none transition-colors"
                  required
                />
              </div>
            </div>
            
            {/* Scope */}
            <div className="space-y-4">
              <h4 className="text-xs font-mono text-cyber-accent/70 uppercase tracking-widest border-b border-cyber-border/50 pb-1 mb-3 flex items-center gap-2">
                <Map size={14} /> Scope Definition
              </h4>
              <div>
                <label className="block text-xs font-mono text-cyber-text mb-1 uppercase tracking-wider">Testing Scope / Boundaries</label>
                <textarea 
                  value={scope}
                  onChange={e => setScope(e.target.value)}
                  placeholder="Define strict network/domain bounds..."
                  className="w-full bg-cyber-darkest border border-cyber-border focus:border-cyber-accent rounded p-2 text-white font-mono text-sm focus:outline-none transition-colors min-h-[80px]"
                  required
                />
              </div>
            </div>

            {/* Profile */}
            <div className="space-y-4">
              <h4 className="text-xs font-mono text-cyber-accent/70 uppercase tracking-widest border-b border-cyber-border/50 pb-1 mb-3 flex items-center gap-2">
                <Crosshair size={14} /> Scan Configuration
              </h4>
              <div>
                <label className="block text-xs font-mono text-cyber-text mb-1 uppercase tracking-wider">Scan Profile</label>
                <select 
                  value={scanProfile}
                  onChange={e => setScanProfile(e.target.value)}
                  className="w-full bg-cyber-darkest border border-cyber-border focus:border-cyber-accent rounded p-2 text-white font-mono text-sm focus:outline-none transition-colors"
                >
                  <option value="passive">PASSIVE (Reconnaissance only)</option>
                  <option value="safe">SAFE (Non-intrusive)</option>
                  <option value="standard">STANDARD (Default)</option>
                  <option value="active">ACTIVE (Intrusive attacks)</option>
                  <option value="deep">DEEP (Comprehensive)</option>
                </select>
              </div>
            </div>

            {/* Auth */}
            <div className="bg-cyber-darkest border border-red-900/50 rounded p-4 relative overflow-hidden">
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-red-500"></div>
              <label className="flex items-start gap-3 cursor-pointer ml-2">
                <input 
                  type="checkbox" 
                  checked={authConfirmed}
                  onChange={e => setAuthConfirmed(e.target.checked)}
                  className="mt-1 flex-shrink-0 w-4 h-4 text-cyber-accent rounded bg-cyber-darker border-cyber-border focus:ring-cyber-accent"
                />
                <div className="text-sm">
                  <strong className="block text-white font-mono uppercase tracking-widest mb-1 text-xs text-red-400 flex items-center gap-2">
                    <ShieldCheck size={14} /> Authorization Required
                  </strong>
                  <span className="text-cyber-text text-xs leading-relaxed font-mono uppercase">
                    I confirm explicit authorization to perform security testing against the target within the stated scope.
                  </span>
                </div>
              </label>
            </div>

            <button 
              type="submit" 
              disabled={!isValid || creating}
              className="w-full flex items-center justify-center gap-2 bg-cyber-accent hover:bg-cyber-accent/80 text-black font-bold uppercase tracking-widest py-3 px-4 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
            >
              <Radar size={16} className={creating ? 'animate-spin' : ''} />
              {creating ? 'INITIALIZING...' : 'INITIALIZE ASSESSMENT'}
            </button>
          </form>
        </div>

        {/* Assessments List Panel */}
        <div className="xl:col-span-2 bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col h-fit min-h-[400px]">
          <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Database size={18} className="text-cyber-accent" />
              <h3 className="font-mono text-white tracking-widest uppercase text-sm">Security Assessments</h3>
            </div>
            <span className="bg-cyber-dark text-cyber-accent border border-cyber-accent/30 px-2 py-0.5 rounded text-xs font-mono">
              {assessments.length} RECORD(S)
            </span>
          </div>

          <div className="p-0 flex-1">
            {loading ? (
              <div className="p-12 text-center text-cyber-accent font-mono animate-pulse">
                RETRIEVING ASSESSMENT TELEMETRY...
              </div>
            ) : assessments.length === 0 ? (
              <div className="p-16 text-center flex flex-col items-center justify-center">
                <Crosshair size={48} className="text-cyber-border mb-4" />
                <h4 className="text-white font-mono uppercase tracking-widest mb-2">NO ASSESSMENTS DETECTED</h4>
                <p className="text-cyber-text text-sm max-w-sm mx-auto font-mono uppercase">
                  Initialize an authorized security assessment to begin analysis.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-cyber-darkest/50 border-b border-cyber-border text-cyber-text text-xs font-mono uppercase tracking-wider">
                      <th className="py-3 px-4 font-medium">Identity</th>
                      <th className="py-3 px-4 font-medium">Target</th>
                      <th className="py-3 px-4 font-medium">Profile</th>
                      <th className="py-3 px-4 font-medium">Status</th>
                      <th className="py-3 px-4 font-medium text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="text-sm">
                    {assessments.map(a => (
                      <tr key={a.id} className="border-b border-cyber-border/50 hover:bg-cyber-dark/40 transition-colors group">
                        <td className="py-3 px-4">
                          <div className="font-medium text-white">{a.name}</div>
                          <div className="text-xs text-cyber-text font-mono mt-0.5">{new Date(a.created_at).toLocaleDateString()}</div>
                        </td>
                        <td className="py-3 px-4 text-cyber-accent font-mono text-xs">{a.target}</td>
                        <td className="py-3 px-4">
                          <span className="bg-cyber-dark text-cyber-textBright border border-cyber-border px-2 py-1 rounded text-xs uppercase font-mono tracking-wider">
                            {a.scan_profile}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-1.5">
                            <Activity size={14} className={a.status === 'completed' ? 'text-green-500' : 'text-cyber-accent'} />
                            <span className={`uppercase font-mono text-xs tracking-wider ${a.status === 'completed' ? 'text-green-500' : 'text-cyber-textBright'}`}>
                              {a.status}
                            </span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => onSelectAssessment(a.id)}
                            className="text-cyber-accent border border-cyber-accent hover:bg-cyber-accent hover:text-black text-xs font-bold px-3 py-1.5 rounded transition-colors uppercase tracking-widest font-mono"
                          >
                            Open Console
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
      </div>
    </div>
  );
}
