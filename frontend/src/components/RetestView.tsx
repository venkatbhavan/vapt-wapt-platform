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
    case 'completed': return 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20';
    case 'running': return 'bg-blue-500/10 text-blue-500 border border-blue-500/20';
    case 'requested': return 'bg-yellow-500/10 text-yellow-500 border border-yellow-500/20';
    case 'failed': return 'bg-red-500/10 text-red-500 border border-red-500/20';
    default: return 'bg-gray-800 text-gray-400 border border-gray-700';
  }
};

const getResultColor = (result?: string | null) => {
  if (!result) return 'text-gray-500';
  switch (result) {
    case 'fixed': return 'text-emerald-500';
    case 'still_present': return 'text-red-500';
    case 'changed': return 'text-orange-500';
    case 'inconclusive': return 'text-yellow-500';
    default: return 'text-gray-400';
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
      const res = await fetch(`http://localhost:8000/api/assessments/${assessmentId}/retests`);
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
      const res = await fetch(`http://localhost:8000/api/findings/${findingId}/retests`, {
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
      <div className="text-gray-400 p-8 flex gap-3 items-center">
        <Activity className="animate-spin" size={20} /> Loading retests...
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <button onClick={onBack} className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors">
          <ArrowLeft size={16} /> Back to Dashboard
        </button>
        <div className="bg-red-500/10 border border-red-500 text-red-500 p-4 rounded-lg flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <AlertTriangle size={20} />
            <p>{error}</p>
          </div>
          <button onClick={fetchRetests} className="px-3 py-1 bg-red-500/20 hover:bg-red-500/30 rounded transition-colors">
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
        <button onClick={onBack} className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors">
          <ArrowLeft size={16} /> Back to Dashboard
        </button>
        <div className="flex items-center gap-2 text-indigo-400">
          <ShieldCheck size={20} />
          <h2 className="text-xl font-bold">Retest Dashboard</h2>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-gray-900 border border-gray-800 p-4 rounded-lg">
          <p className="text-sm text-gray-400">Total Retests</p>
          <p className="text-2xl font-bold text-white">{total}</p>
        </div>
        <div className="bg-gray-900 border border-gray-800 p-4 rounded-lg">
          <p className="text-sm text-gray-400">Completed</p>
          <p className="text-2xl font-bold text-blue-400">{completed}</p>
        </div>
        <div className="bg-gray-900 border border-gray-800 p-4 rounded-lg">
          <p className="text-sm text-gray-400">Fixed</p>
          <p className="text-2xl font-bold text-emerald-500">{fixed}</p>
        </div>
        <div className="bg-gray-900 border border-gray-800 p-4 rounded-lg">
          <p className="text-sm text-gray-400">Still Present</p>
          <p className="text-2xl font-bold text-red-500">{stillPresent}</p>
        </div>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <div className="flex flex-col md:flex-row gap-4 justify-between mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={16} />
            <input
              type="text"
              placeholder="Search by ID, outcome, rationale..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-gray-950 border border-gray-800 rounded focus:border-indigo-500 focus:outline-none text-gray-200"
            />
          </div>
          <div className="flex gap-4">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-gray-950 border border-gray-800 rounded px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Statuses</option>
              <option value="requested">Requested</option>
              <option value="running">Running</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
            <select
              value={resultFilter}
              onChange={(e) => setResultFilter(e.target.value)}
              className="bg-gray-950 border border-gray-800 rounded px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Outcomes</option>
              <option value="fixed">Fixed</option>
              <option value="still_present">Still Present</option>
              <option value="changed">Changed</option>
              <option value="inconclusive">Inconclusive</option>
            </select>
            {(statusFilter || resultFilter || search) && (
              <button
                onClick={() => { setStatusFilter(''); setResultFilter(''); setSearch(''); }}
                className="p-2 text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 rounded transition-colors"
                title="Reset Filters"
              >
                <X size={16} />
              </button>
            )}
          </div>
        </div>

        {filteredRetests.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            {retests.length === 0 ? "No retests have been requested for this assessment yet." : "No retests match the current filters."}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-gray-800 text-xs uppercase tracking-wider text-gray-500">
                  <th className="p-4 font-medium">Retest ID</th>
                  <th className="p-4 font-medium">Status</th>
                  <th className="p-4 font-medium">Outcome</th>
                  <th className="p-4 font-medium">Target Finding</th>
                  <th className="p-4 font-medium">Requested</th>
                  <th className="p-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/50">
                {filteredRetests.map((retest) => (
                  <tr key={retest.id} className="hover:bg-gray-800/20 transition-colors">
                    <td className="p-4 text-sm font-mono text-gray-400">#{retest.id}</td>
                    <td className="p-4">
                      <span className={`px-2.5 py-1 rounded text-xs uppercase font-medium ${getStatusColor(retest.status)}`}>
                        {retest.status}
                      </span>
                    </td>
                    <td className="p-4">
                      {retest.result ? (
                        <span className={`text-sm font-medium uppercase tracking-wide ${getResultColor(retest.result.result)}`}>
                          {retest.result.result.replace('_', ' ')}
                        </span>
                      ) : (
                        <span className="text-gray-600 text-sm">-</span>
                      )}
                      {retest.result?.rationale && (
                        <p className="text-xs text-gray-500 mt-1 max-w-xs truncate" title={retest.result.rationale}>
                          {retest.result.rationale}
                        </p>
                      )}
                    </td>
                    <td className="p-4">
                      <div className="flex flex-col gap-1">
                        <button
                          onClick={() => onViewFinding(retest.finding_id)}
                          className="text-sm text-blue-400 hover:text-blue-300 text-left hover:underline"
                        >
                          Finding #{retest.finding_id}
                        </button>
                        {retest.result?.current_finding_id && retest.result.current_finding_id !== retest.finding_id && (
                          <button
                            onClick={() => onViewFinding(retest.result!.current_finding_id!)}
                            className="text-xs text-orange-400 hover:text-orange-300 text-left hover:underline"
                          >
                            → View New: #{retest.result.current_finding_id}
                          </button>
                        )}
                      </div>
                    </td>
                    <td className="p-4 text-sm text-gray-400">
                      {new Date(retest.requested_at).toLocaleString()}
                    </td>
                    <td className="p-4">
                      <button
                        onClick={() => handleRetest(retest.finding_id)}
                        disabled={triggeringId === retest.finding_id || retest.status === 'requested' || retest.status === 'running'}
                        className="flex items-center gap-2 text-sm bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-800 disabled:text-gray-500 text-white px-3 py-1.5 rounded transition-colors"
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
  );
}
