import { useState, useEffect } from 'react';
import { ArrowLeft, RefreshCw, AlertTriangle, ShieldCheck, Activity, Search, X } from 'lucide-react';
import { RetestRequest } from '../types/retest';

interface RetestViewProps {
  assessmentId: number;
  onBack: () => void;
  onViewFinding: (findingId: number) => void;
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'completed': return 'border-emerald-500 text-emerald-500 bg-emerald-500/10';
    case 'running': return 'border-cyber-accent text-cyber-accent bg-cyber-accent/10';
    case 'requested': return 'border-yellow-500 text-yellow-500 bg-yellow-500/10';
    case 'failed': return 'border-red-500 text-red-500 bg-red-500/10';
    default: return 'border-cyber-border text-cyber-text bg-cyber-dark';
  }
};

const getResultColor = (result?: string | null) => {
  if (!result) return 'text-cyber-text';
  switch (result) {
    case 'fixed': return 'text-emerald-500';
    case 'still_present': return 'text-red-500';
    case 'changed': return 'text-orange-500';
    case 'inconclusive': return 'text-yellow-500';
    default: return 'text-cyber-text';
  }
};

export function RetestView({ assessmentId, onBack, onViewFinding }: RetestViewProps) {
  const [retests, setRetests] = useState<RetestRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [resultFilter, setResultFilter] = useState<string>('');

  const [triggeringId, setTriggeringId] = useState<number | null>(null);

  const fetchRetests = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/assessments/${assessmentId}/retests`);
      if (!res.ok) throw new Error('Failed to fetch retests');
      const data: RetestRequest[] = await res.json();
      setRetests(data);
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
      else setError('API Error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRetests();
  }, [assessmentId]);

  const handleRetest = async (findingId: number) => {
    setTriggeringId(findingId);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/findings/${findingId}/retests`, {
        method: 'POST'
      });
      if (!res.ok) throw new Error('Failed to trigger retest');
      await fetchRetests();
    } catch (err: unknown) {
      if (err instanceof Error) alert(err.message);
    } finally {
      setTriggeringId(null);
    }
  };

  if (loading) {
    return (
      <div className="text-cyber-text p-8 flex gap-3 items-center font-mono">
        <Activity className="animate-spin text-cyber-accent" size={20} /> LOADING RETESTS...
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <button onClick={onBack} className="flex items-center gap-2 text-cyber-text hover:text-white transition-colors font-mono uppercase text-sm tracking-wider">
          <ArrowLeft size={16} /> Back to Dashboard
        </button>
        <div className="bg-red-500/10 border border-red-500 text-red-500 p-4 rounded flex items-center justify-between gap-3 font-mono">
          <div className="flex items-center gap-3">
            <AlertTriangle size={20} />
            <p>{error}</p>
          </div>
          <button onClick={fetchRetests} className="bg-red-500 hover:bg-red-600 text-black font-bold uppercase tracking-widest py-2 px-4 rounded transition-colors font-mono text-sm">
            Retry
          </button>
        </div>
      </div>
    );
  }

  const filteredRetests = retests.filter(r => {
    if (statusFilter && r.status !== statusFilter) return false;
    if (resultFilter) {
      if (!r.result || r.result.result !== resultFilter) return false;
    }
    if (search) {
      const s = search.toLowerCase();
      const matchId = r.id.toString().includes(s) || r.finding_id.toString().includes(s);
      const matchResult = r.result?.result.toLowerCase().includes(s);
      const matchRationale = r.result?.rationale.toLowerCase().includes(s);
      return matchId || matchResult || matchRationale;
    }
    return true;
  });

  const total = retests.length;
  const completed = retests.filter(r => r.status === 'completed').length;
  const fixed = retests.filter(r => r.result?.result === 'fixed').length;
  const stillPresent = retests.filter(r => r.result?.result === 'still_present').length;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <button onClick={onBack} className="flex items-center gap-2 text-cyber-text hover:text-white transition-colors font-mono uppercase text-sm tracking-wider">
          <ArrowLeft size={16} /> Back to Dashboard
        </button>
        <div className="flex items-center gap-2 text-cyber-accent">
          <ShieldCheck size={20} />
          <h2 className="text-xl font-bold font-mono tracking-widest uppercase">Retest Dashboard</h2>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-4">
          <p className="font-mono uppercase text-xs tracking-wider text-cyber-text mb-1">Total Retests</p>
          <p className="text-2xl font-bold text-white font-mono">{total}</p>
        </div>
        <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-4">
          <p className="font-mono uppercase text-xs tracking-wider text-cyber-text mb-1">Completed</p>
          <p className="text-2xl font-bold text-cyber-accent font-mono">{completed}</p>
        </div>
        <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-4">
          <p className="font-mono uppercase text-xs tracking-wider text-cyber-text mb-1">Fixed</p>
          <p className="text-2xl font-bold text-emerald-500 font-mono">{fixed}</p>
        </div>
        <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-4">
          <p className="font-mono uppercase text-xs tracking-wider text-cyber-text mb-1">Still Present</p>
          <p className="text-2xl font-bold text-red-500 font-mono">{stillPresent}</p>
        </div>
      </div>

      <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
        <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
          <RefreshCw size={18} className="text-cyber-accent" />
          <h3 className="font-mono text-white tracking-widest uppercase text-sm">RETESTS</h3>
        </div>
        <div className="p-6">
          <div className="flex flex-col md:flex-row gap-4 justify-between mb-6">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-cyber-text" size={16} />
              <input
                type="text"
                placeholder="Search by ID, outcome, rationale..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-cyber-darkest border border-cyber-border rounded focus:border-cyber-accent focus:outline-none text-cyber-textBright font-mono text-sm"
              />
            </div>
            <div className="flex gap-4">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-cyber-darkest border border-cyber-border rounded px-3 py-2 text-sm text-cyber-textBright focus:outline-none focus:border-cyber-accent font-mono"
              >
                <option value="">ALL STATUSES</option>
                <option value="requested">REQUESTED</option>
                <option value="running">RUNNING</option>
                <option value="completed">COMPLETED</option>
                <option value="failed">FAILED</option>
              </select>
              <select
                value={resultFilter}
                onChange={(e) => setResultFilter(e.target.value)}
                className="bg-cyber-darkest border border-cyber-border rounded px-3 py-2 text-sm text-cyber-textBright focus:outline-none focus:border-cyber-accent font-mono"
              >
                <option value="">ALL OUTCOMES</option>
                <option value="fixed">FIXED</option>
                <option value="still_present">STILL PRESENT</option>
                <option value="changed">CHANGED</option>
                <option value="inconclusive">INCONCLUSIVE</option>
              </select>
              {(statusFilter || resultFilter || search) && (
                <button
                  onClick={() => { setStatusFilter(''); setResultFilter(''); setSearch(''); }}
                  className="p-2 text-cyber-text hover:text-white border border-cyber-border hover:border-cyber-text/70 rounded transition-colors"
                  title="Reset Filters"
                >
                  <X size={16} />
                </button>
              )}
            </div>
          </div>

          {filteredRetests.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <ShieldCheck className="text-cyber-border mb-4" size={48} />
              <h3 className="text-white font-mono uppercase tracking-widest mb-2">No Retests Found</h3>
              <p className="text-cyber-text text-sm font-mono">
                {retests.length === 0 ? "No retests have been requested for this assessment yet." : "No retests match the current filters."}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-cyber-darkest/50 border-b border-cyber-border text-cyber-text text-xs font-mono uppercase tracking-wider">
                    <th className="p-4 font-medium">Retest ID</th>
                    <th className="p-4 font-medium">Status</th>
                    <th className="p-4 font-medium">Outcome</th>
                    <th className="p-4 font-medium">Target Finding</th>
                    <th className="p-4 font-medium">Requested</th>
                    <th className="p-4 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/50">
                  {filteredRetests.map((retest) => (
                    <tr key={retest.id} className="hover:bg-cyber-dark/20 transition-colors">
                      <td className="p-4 text-sm font-mono text-cyber-text">#{retest.id}</td>
                      <td className="p-4">
                        <span className={`border px-2 py-0.5 rounded text-xs font-mono uppercase ${getStatusColor(retest.status)}`}>
                          {retest.status}
                        </span>
                      </td>
                      <td className="p-4">
                        {retest.result ? (
                          <span className={`text-sm font-medium uppercase tracking-wide font-mono ${getResultColor(retest.result.result)}`}>
                            {retest.result.result.replace('_', ' ')}
                          </span>
                        ) : (
                          <span className="text-cyber-border text-sm">-</span>
                        )}
                        {retest.result?.rationale && (
                          <p className="text-xs text-cyber-text mt-1 max-w-xs truncate font-mono" title={retest.result.rationale}>
                            {retest.result.rationale}
                          </p>
                        )}
                      </td>
                      <td className="p-4">
                        <div className="flex flex-col gap-1">
                          <button
                            onClick={() => onViewFinding(retest.finding_id)}
                            className="text-sm text-cyber-accent hover:text-cyber-accent text-left hover:underline font-mono"
                          >
                            Finding #{retest.finding_id}
                          </button>
                          {retest.result?.current_finding_id && retest.result.current_finding_id !== retest.finding_id && (
                            <button
                              onClick={() => onViewFinding(retest.result!.current_finding_id!)}
                              className="text-xs text-orange-400 hover:text-orange-300 text-left hover:underline font-mono"
                            >
                              → View New: #{retest.result.current_finding_id}
                            </button>
                          )}
                        </div>
                      </td>
                      <td className="p-4 text-sm text-cyber-text font-mono">
                        {new Date(retest.requested_at).toLocaleString()}
                      </td>
                      <td className="p-4 text-right flex justify-end">
                        <button
                          onClick={() => handleRetest(retest.finding_id)}
                          disabled={triggeringId === retest.finding_id || retest.status === 'requested' || retest.status === 'running'}
                          className="flex items-center gap-2 border border-cyber-accent text-cyber-accent hover:bg-cyber-accent hover:text-black font-bold uppercase tracking-widest py-2 px-4 rounded transition-colors font-mono text-sm disabled:opacity-50 disabled:hover:bg-transparent disabled:hover:text-cyber-accent"
                        >
                          {triggeringId === retest.finding_id ? <Activity size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                          Retest Again
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
  );
}
