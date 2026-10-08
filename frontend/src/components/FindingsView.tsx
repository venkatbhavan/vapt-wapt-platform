import { useState, useEffect } from 'react';
import { ArrowLeft, AlertTriangle, Shield, CheckCircle, ChevronRight, Activity, FileText, ShieldAlert, RefreshCw } from 'lucide-react';
import { RetestRequest } from '../types/retest';
interface ScanJob {
  id: number;
  assessment_id: number;
  scan_profile: string;
  status: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}
interface Finding {
  id: number;
  scan_job_id: number;
  title: string;
  description: string;
  severity: string;
  confidence: string;
  category: string;
  location: string;
  impact: string;
  remediation: string;
  status: string;
  risk_score: number | null;
  risk_level: string | null;
  risk_rationale: string | null;
  created_at: string;
  updated_at: string;
}
interface Evidence {
  id: number;
  finding_id: number;
  evidence_type: string;
  title: string;
  content: string;
  source: string;
  created_at: string;
}
interface FindingsViewProps {
  assessmentId: number;
  initialJobId?: number | null;
  initialFindingId?: number | null;
  onBack: () => void;
}
const getSeverityColor = (severity: string) => {
  switch (severity?.toLowerCase()) {
    case 'critical': return 'text-purple-500 bg-purple-500/10 border-purple-500/20';
    case 'high': return 'text-red-500 bg-red-500/10 border-red-500/20';
    case 'medium': return 'text-orange-500 bg-orange-500/10 border-orange-500/20';
    case 'low': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
    case 'info': return 'text-cyber-accent bg-cyber-accent/10 border-cyber-accent/20';
    default: return 'text-cyber-text bg-cyber-dark border-cyber-border';
  }
};
const getRiskColor = (riskLevel: string | null) => {
  switch (riskLevel?.toLowerCase()) {
    case 'critical': return 'text-purple-400';
    case 'high': return 'text-red-400';
    case 'medium': return 'text-orange-400';
    case 'low': return 'text-yellow-400';
    case 'info': return 'text-cyber-accent';
    default: return 'text-cyber-text';
  }
};
export function FindingsView({ assessmentId, initialJobId, initialFindingId, onBack }: FindingsViewProps) {
  const [scanJobs, setScanJobs] = useState<ScanJob[]>([]);
  const [selectedJob, setSelectedJob] = useState<ScanJob | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [retestHistory, setRetestHistory] = useState<RetestRequest[]>([]);
  const [loadingRetests, setLoadingRetests] = useState(false);
  const [triggeringRetest, setTriggeringRetest] = useState(false);
  const [retestError, setRetestError] = useState<string | null>(null);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [loadingFindings, setLoadingFindings] = useState(false);
  const [loadingEvidence, setLoadingEvidence] = useState(false);
  const [startingScan, setStartingScan] = useState(false);
  const [error, setError] = useState('');
  const fetchScanJobs = async () => {
    setLoadingJobs(true);
    setError('');
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}`}/api/assessments/${assessmentId}/scan-jobs`);
      if (!res.ok) throw new Error('Failed to fetch scan jobs');
      const data: ScanJob[] = await res.json();
      // Sort jobs newest first
      data.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      setScanJobs(data);
      if (initialJobId && !selectedJob) {
        const job = data.find(j => j.id === initialJobId);
        setSelectedJob(job || data[0]);
      } else if (data.length > 0 && !selectedJob) {
        setSelectedJob(data[0]);
      } else if (selectedJob) {
        // Refresh selected job
        const updated = data.find(j => j.id === selectedJob.id);
        if (updated) setSelectedJob(updated);
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message || 'API error fetching scan jobs');
      } else {
        setError('API error fetching scan jobs');
      }
    } finally {
      setLoadingJobs(false);
    }
  };
  useEffect(() => {
    fetchScanJobs();
  }, [assessmentId]);
  useEffect(() => {
    setSelectedFinding(null);
    setEvidenceList([]);
    if (!selectedJob) {
      setFindings([]);
      return;
    }
    if (selectedJob.status === 'completed' || selectedJob.status === 'failed') {
      fetchFindings(selectedJob.id);
    } else {
      setFindings([]);
      // Auto refresh if job is queued or running
      const timer = setTimeout(() => {
        fetchScanJobs();
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [selectedJob]);
  const fetchFindings = async (jobId: number) => {
    setLoadingFindings(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}`}/api/scan-jobs/${jobId}/findings`);
      if (!res.ok) throw new Error('Failed to fetch findings');
      const data: Finding[] = await res.json();
      setFindings(data);
      if (initialFindingId && !selectedFinding) {
        const f = data.find(x => x.id === initialFindingId);
        if (f) handleSelectFinding(f);
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message || 'API error fetching findings');
      } else {
        setError('API error fetching findings');
      }
    } finally {
      setLoadingFindings(false);
    }
  };
  const handleSelectFinding = async (finding: Finding) => {
    setSelectedFinding(finding);
    setLoadingEvidence(true);
    setLoadingRetests(true);
    try {
      const [evRes, retRes] = await Promise.all([
          fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/findings/` + finding.id + "/evidence?assessment_id=" + assessmentId),
          fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/findings/` + finding.id + "/retests?assessment_id=" + assessmentId)
      ]);
      if (evRes.ok) {
          const data: Evidence[] = await evRes.json();
          setEvidenceList(data);
      } else {
          setEvidenceList([]);
      }
      if (retRes.ok) {
          const data: RetestRequest[] = await retRes.json();
          data.sort((a, b) => new Date(b.requested_at).getTime() - new Date(a.requested_at).getTime());
          setRetestHistory(data);
      } else {
          setRetestHistory([]);
      }
    } catch (err) {
      console.error(err);
      setEvidenceList([]);
      setRetestHistory([]);
    } finally {
      setLoadingEvidence(false);
      setLoadingRetests(false);
    }
  };
const handleTriggerRetest = async () => {
  if (!selectedFinding) return;
  setTriggeringRetest(true);
    setRetestError(null);
  try {
    const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/findings/` + selectedFinding.id + "/retests?assessment_id=" + assessmentId, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    if (res.ok) {
      // Refresh retest history
      const retRes = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/findings/` + selectedFinding.id + "/retests?assessment_id=" + assessmentId);
      if (retRes.ok) {
          const data: RetestRequest[] = await retRes.json();
          data.sort((a, b) => new Date(b.requested_at).getTime() - new Date(a.requested_at).getTime());
          setRetestHistory(data);
      }
    }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setRetestError(err.message);
      } else {
        setRetestError('Failed to trigger retest');
      }
  } finally {
      setTriggeringRetest(false);
  }
};
  const [showActiveModal, setShowActiveModal] = useState(false);
  const handleRunScan = async (confirmed = false) => {
    setStartingScan(true);
    setError('');
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}`}/api/assessments/${assessmentId}/scan-jobs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ active_scan_confirmed: confirmed })
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        if (res.status === 400 && errData.detail === "Explicit confirmation is required for active/deep scans") {
          setShowActiveModal(true);
          setStartingScan(false);
          return;
        }
        throw new Error(errData.detail || 'Failed to start scan');
      }
      setShowActiveModal(false);
      await fetchScanJobs();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message || 'Error starting scan');
      } else {
        setError('Error starting scan');
      }
    } finally {
      if (!showActiveModal) {
        setStartingScan(false);
      }
    }
  };
  return (
    <div className="space-y-6">
      {/* Active Scan Confirmation Modal */}
      {showActiveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-cyber-darker border border-red-900/50 rounded-lg p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-xl font-semibold text-red-500 mb-2 flex items-center gap-2">
              <ShieldAlert size={24} />
              Active Scan Warning
            </h3>
            <p className="text-cyber-textBright mb-6 text-sm">
              You are about to launch an active/deep scan. This may send intrusive payloads, test for vulnerabilities aggressively, and potentially impact the target's availability. Do you have explicit authorization to perform an active scan on this target?
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => { setShowActiveModal(false); setStartingScan(false); }}
                className="px-4 py-2 text-sm font-medium text-cyber-text hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={() => handleRunScan(true)}
                className="px-4 py-2 text-sm font-medium bg-red-600 text-white rounded hover:bg-red-700"
              >
                Confirm & Run Scan
              </button>
            </div>
          </div>
        </div>
      )}
      <div className="flex justify-between items-center">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-cyber-text hover:text-white transition-colors"
        >
          <ArrowLeft size={16} /> Back to Assessments
        </button>
        <button
          onClick={() => handleRunScan(false)}
          disabled={startingScan}
          className="flex items-center gap-2 bg-cyber-dark hover:bg-cyber-border text-cyber-accent border border-cyber-accent/50 shadow-[0_0_10px_rgba(0,240,255,0.1)] text-white px-4 py-2 rounded transition-colors disabled:opacity-50"
        >
          <Activity size={16} />
          {startingScan ? 'Starting...' : 'Run New Scan'}
        </button>
      </div>
      {error && (
        <div className="bg-red-500/10 border border-red-500 text-red-500 p-4 rounded-lg flex items-center gap-3">
          <AlertTriangle size={20} />
          <p>{error}</p>
        </div>
      )}
      {/* Top Controls: Scan Job Selection */}
      <div className="bg-cyber-darker border border-cyber-border rounded-lg p-6">
        <h3 className="text-xl font-bold text-white mb-4">Scan Jobs</h3>
        {loadingJobs && scanJobs.length === 0 ? (
          <p className="text-cyber-text">Loading scan jobs...</p>
        ) : scanJobs.length === 0 ? (
          <p className="text-cyber-text">No scan jobs run for this assessment yet.</p>
        ) : (
          <div className="flex gap-4 overflow-x-auto pb-2">
            {scanJobs.map(job => (
              <button
                key={job.id}
                onClick={() => setSelectedJob(job)}
                className={`flex flex-col text-left p-3 rounded border min-w-[200px] transition-colors ${
                  selectedJob?.id === job.id
                    ? 'bg-blue-900/20 border-cyber-accent text-blue-100'
                    : 'bg-cyber-darkest border-cyber-border text-cyber-text hover:border-cyber-border'
                }`}
              >
                <div className="flex items-center justify-between mb-1 w-full">
                  <span className="font-mono text-xs">Job #{job.id}</span>
                  <span className={`text-[10px] uppercase px-1.5 py-0.5 rounded ${
                    job.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                    job.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                    'bg-yellow-500/20 text-yellow-400'
                  }`}>
                    {job.status}
                  </span>
                </div>
                <span className="text-sm truncate w-full">{new Date(job.created_at).toLocaleString()}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      {/* Main split view: Findings List & Detail Panel */}
      {selectedJob && (
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Left: Findings List */}
          <div className="flex-1 bg-cyber-darker border border-cyber-border rounded-lg p-6">
            <h3 className="text-xl font-bold text-white mb-4">
              Findings for Job #{selectedJob.id}
            </h3>
            {['queued', 'running'].includes(selectedJob.status) ? (
              <div className="flex items-center gap-3 text-yellow-500 bg-yellow-500/10 p-4 rounded border border-yellow-500/20">
                <Activity className="animate-spin" size={20} />
                <p>Scan job is currently {selectedJob.status}. Findings will appear when completed.</p>
              </div>
            ) : selectedJob.status === 'failed' ? (
              <div className="text-red-400 bg-red-950/30 p-4 rounded border border-red-900/50">
                <p>Scan job failed.</p>
                <p className="text-sm mt-1 opacity-80">{selectedJob.error_message}</p>
              </div>
            ) : loadingFindings ? (
              <p className="text-cyber-text">Loading findings...</p>
            ) : findings.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-8 text-cyber-text border border-dashed border-cyber-border rounded bg-cyber-darkest/50">
                <CheckCircle size={32} className="mb-2 text-green-500/50" />
                <p>No findings reported.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {findings.map(finding => (
                  <button
                    key={finding.id}
                    onClick={() => handleSelectFinding(finding)}
                    className={`w-full text-left flex items-center justify-between p-3 rounded border transition-colors ${
                      selectedFinding?.id === finding.id
                        ? 'bg-cyber-dark border-cyber-border'
                        : 'bg-cyber-darkest border-cyber-border hover:border-cyber-border'
                    }`}
                  >
                    <div className="flex items-center gap-4 flex-1 min-w-0">
                      <span className={`px-2.5 py-1 rounded text-xs font-medium border uppercase w-24 text-center shrink-0 ${getSeverityColor(finding.severity)}`}>
                        {finding.severity}
                      </span>
                      <div className="truncate">
                        <p className="text-white font-medium truncate">{finding.title}</p>
                        <p className="text-xs text-cyber-text mt-0.5">
                          Risk: <span className={getRiskColor(finding.risk_level)}>{finding.risk_level?.toUpperCase() || 'N/A'}</span> ({finding.risk_score?.toFixed(2) || '-'})
                        </p>
                      </div>
                    </div>
                    <ChevronRight size={18} className="text-cyber-border shrink-0 ml-2" />
                  </button>
                ))}
              </div>
            )}
          </div>
          {/* Right: Detail Panel */}
          {selectedFinding && (
            <div className="flex-1 bg-cyber-darker border border-cyber-border rounded-lg p-6 flex flex-col h-full max-h-[800px] overflow-y-auto">
              <div className="flex items-start justify-between mb-4 border-b border-cyber-border pb-4">
                <div>
                  <h2 className="text-2xl font-bold text-white mb-2">{selectedFinding.title}</h2>
                  <div className="flex flex-wrap gap-2 text-xs">
                    <span className={`px-2 py-1 rounded border ${getSeverityColor(selectedFinding.severity)}`}>
                      Severity: {selectedFinding.severity.toUpperCase()}
                    </span>
                    <span className={`px-2 py-1 rounded border bg-cyber-dark border-cyber-border text-cyber-textBright`}>
                      Confidence: {selectedFinding.confidence?.toUpperCase() || 'N/A'}
                    </span>
                    <span className={`px-2 py-1 rounded border bg-cyber-dark border-cyber-border text-cyber-textBright`}>
                      Status: {selectedFinding.status.toUpperCase()}
                    </span>
                  </div>
                </div>
              </div>
              <div className="space-y-6 text-sm text-cyber-textBright">
                {/* Risk Panel */}
                <div className="bg-cyber-darkest border border-cyber-border rounded p-4">
                  <h4 className="font-semibold text-white mb-2 flex items-center gap-2">
                    <Shield size={16} className={getRiskColor(selectedFinding.risk_level)} />
                    Risk Assessment
                  </h4>
                  <div className="grid grid-cols-2 gap-4 mb-2">
                    <div>
                      <p className="text-cyber-text">Risk Level</p>
                      <p className={`font-medium ${getRiskColor(selectedFinding.risk_level)}`}>
                        {selectedFinding.risk_level?.toUpperCase() || 'Unknown'}
                      </p>
                    </div>
                    <div>
                      <p className="text-cyber-text">Risk Score</p>
                      <p className="font-medium text-white">{selectedFinding.risk_score?.toFixed(2) || 'N/A'}</p>
                    </div>
                  </div>
                  {selectedFinding.risk_rationale && (
                    <div className="bg-cyber-darker p-2 rounded text-xs text-cyber-text mt-2">
                      {selectedFinding.risk_rationale}
                    </div>
                  )}
                </div>
                <div>
                  <h4 className="font-semibold text-white mb-1">Description</h4>
                  <p className="whitespace-pre-wrap text-cyber-text">
                    {selectedFinding.description || 'No description provided.'}
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  {selectedFinding.category && (
                    <div>
                      <h4 className="font-semibold text-white mb-1">Category</h4>
                      <p className="text-cyber-text">{selectedFinding.category}</p>
                    </div>
                  )}
                  {selectedFinding.location && (
                    <div>
                      <h4 className="font-semibold text-white mb-1">Location</h4>
                      <p className="text-cyber-text">{selectedFinding.location}</p>
                    </div>
                  )}
                </div>
                {selectedFinding.impact && (
                  <div>
                    <h4 className="font-semibold text-white mb-1">Impact</h4>
                    <p className="whitespace-pre-wrap text-cyber-text">{selectedFinding.impact}</p>
                  </div>
                )}
                {selectedFinding.remediation && (
                  <div>
                    <h4 className="font-semibold text-white mb-1">Remediation</h4>
                    <p className="whitespace-pre-wrap text-cyber-text">{selectedFinding.remediation}</p>
                  </div>
                )}
{/* Retest History Section */}
                  <div className="pt-4 border-t border-cyber-border">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-semibold text-white flex items-center gap-2">
                        <RefreshCw size={16} /> Retest History
                      </h4>
                      <button onClick={handleTriggerRetest} disabled={triggeringRetest || (retestHistory.length > 0 && retestHistory[0].status !== 'completed' && retestHistory[0].status !== 'failed')} className="px-3 py-1.5 text-xs bg-cyber-dark hover:bg-cyber-border text-cyber-accent border border-cyber-accent/50 shadow-[0_0_10px_rgba(0,240,255,0.1)] text-white rounded font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 transition-colors">
                        {triggeringRetest ? (<><RefreshCw size={14} className="animate-spin" />Starting...</>) : (<><RefreshCw size={14} />Run Retest</>)}
                      </button>
                    </div>
                    {retestError && <div className="mb-3 p-2 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded">{retestError}</div>}
                    {loadingRetests ? <p className="text-cyber-text italic">Loading retests...</p> : retestHistory.length === 0 ? <p className="text-cyber-text italic">No retests have been requested for this finding yet.</p> : (
                      <div className="space-y-4">
                        {retestHistory.map(rt => (
                          <div key={rt.id} className="bg-cyber-darkest border border-cyber-border rounded p-4">
                            <div className="flex justify-between items-start mb-2">
                              <div>
                                <span className="font-medium text-white flex items-center gap-2">Retest #{rt.id} <span className="px-2 py-0.5 rounded bg-cyber-accent/10 text-cyber-accent text-[10px] uppercase border border-cyber-accent/20">{rt.status}</span></span>
                                <div className="text-xs text-cyber-text mt-1">{new Date(rt.requested_at).toLocaleString()}</div>
                              </div>
                              {rt.result && <span className="px-2 py-1 rounded text-xs font-medium border uppercase bg-cyber-dark text-cyber-textBright border-cyber-border">{rt.result.result.replace('_', ' ')}</span>}
                            </div>
                            {rt.result && (
                              <div className="mt-3 text-sm">
                                <div className="bg-cyber-darker rounded p-3 text-cyber-textBright text-xs border border-cyber-border">{rt.result.rationale}</div>
                                {rt.result.evidence && rt.result.evidence.length > 0 ? (
                                  <div className="mt-4 border-t border-cyber-border pt-3"><h5 className="text-xs font-medium text-cyber-text mb-2">Retest Evidence</h5>
                                  <div className="space-y-2">{rt.result.evidence.map((ev, i) => (<div key={i} className="bg-black border border-cyber-border rounded p-2 text-cyber-text text-xs"><div className="font-semibold text-cyber-textBright mb-1">{ev.title}</div><pre className="whitespace-pre-wrap break-all">{ev.content}</pre></div>))}</div>
                                  </div>
                                ) : (
                                  <div className="mt-2 text-[11px] text-cyber-text italic">No scanner evidence recorded.</div>
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  {/* Evidence Section */}
                <div className="pt-4 border-t border-cyber-border">
                  <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
                    <FileText size={16} /> Evidence
                  </h4>
                  {loadingEvidence ? (
                    <p className="text-cyber-text italic">Loading evidence...</p>
                  ) : evidenceList.length === 0 ? (
                    <p className="text-cyber-text italic">No evidence items attached.</p>
                  ) : (
                    <div className="space-y-3">
                      {evidenceList.map(ev => (
                        <div key={ev.id} className="bg-cyber-darkest border border-cyber-border rounded overflow-hidden">
                          <div className="bg-cyber-darker border-b border-cyber-border px-3 py-2 flex justify-between items-center text-xs">
                            <span className="font-medium text-cyber-textBright">{ev.title || 'Evidence Item'}</span>
                            <span className="text-cyber-text uppercase px-1.5 py-0.5 rounded border border-cyber-border bg-cyber-darkest">
                              {ev.evidence_type}
                            </span>
                          </div>
                          {ev.content && (
                            <div className="p-3">
                              <pre className="text-[11px] text-cyber-text font-mono whitespace-pre-wrap break-all bg-black p-2 rounded">
                                {ev.content}
                              </pre>
                            </div>
                          )}
                          {ev.source && (
                            <div className="px-3 pb-2 text-xs text-cyber-border">
                              Source: {ev.source}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}