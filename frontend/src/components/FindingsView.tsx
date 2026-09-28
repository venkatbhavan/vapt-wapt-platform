import { useState, useEffect } from 'react';
import { ArrowLeft, AlertTriangle, Shield, CheckCircle, ChevronRight, Activity, FileText } from 'lucide-react';

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
    case 'info': return 'text-blue-500 bg-blue-500/10 border-blue-500/20';
    default: return 'text-gray-400 bg-gray-800 border-gray-700';
  }
};

const getRiskColor = (riskLevel: string | null) => {
  switch (riskLevel?.toLowerCase()) {
    case 'critical': return 'text-purple-400';
    case 'high': return 'text-red-400';
    case 'medium': return 'text-orange-400';
    case 'low': return 'text-yellow-400';
    case 'info': return 'text-blue-400';
    default: return 'text-gray-400';
  }
};

export function FindingsView({ assessmentId, initialJobId, initialFindingId, onBack }: FindingsViewProps) {
  const [scanJobs, setScanJobs] = useState<ScanJob[]>([]);
  const [selectedJob, setSelectedJob] = useState<ScanJob | null>(null);
  
  const [findings, setFindings] = useState<Finding[]>([]);
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [loadingFindings, setLoadingFindings] = useState(false);
  const [loadingEvidence, setLoadingEvidence] = useState(false);
  const [startingScan, setStartingScan] = useState(false);
  const [error, setError] = useState('');

  const fetchScanJobs = async () => {
    setLoadingJobs(true);
    setError('');
    try {
      const res = await fetch(`http://localhost:8000/api/assessments/${assessmentId}/scan-jobs`);
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
      const res = await fetch(`http://localhost:8000/api/scan-jobs/${jobId}/findings`);
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
    try {
      const res = await fetch(`http://localhost:8000/api/findings/${finding.id}/evidence`);
      if (!res.ok) throw new Error('Failed to fetch evidence');
      const data: Evidence[] = await res.json();
      setEvidenceList(data);
    } catch (err: unknown) {
      console.error(err);
      // Soft error for evidence so we don't break the UI
      setEvidenceList([]);
    } finally {
      setLoadingEvidence(false);
    }
  };

  const handleRunScan = async () => {
    setStartingScan(true);
    setError('');
    try {
      const res = await fetch(`http://localhost:8000/api/assessments/${assessmentId}/scan-jobs`, {
        method: 'POST'
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to start scan');
      }
      await fetchScanJobs();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message || 'Error starting scan');
      } else {
        setError('Error starting scan');
      }
    } finally {
      setStartingScan(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <button 
          onClick={onBack}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft size={16} /> Back to Assessments
        </button>
        <button
          onClick={handleRunScan}
          disabled={startingScan}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded transition-colors disabled:opacity-50"
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
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <h3 className="text-xl font-bold text-white mb-4">Scan Jobs</h3>
        {loadingJobs && scanJobs.length === 0 ? (
          <p className="text-gray-400">Loading scan jobs...</p>
        ) : scanJobs.length === 0 ? (
          <p className="text-gray-400">No scan jobs run for this assessment yet.</p>
        ) : (
          <div className="flex gap-4 overflow-x-auto pb-2">
            {scanJobs.map(job => (
              <button
                key={job.id}
                onClick={() => setSelectedJob(job)}
                className={`flex flex-col text-left p-3 rounded border min-w-[200px] transition-colors ${
                  selectedJob?.id === job.id 
                    ? 'bg-blue-900/20 border-blue-500 text-blue-100' 
                    : 'bg-gray-950 border-gray-800 text-gray-400 hover:border-gray-600'
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
          <div className="flex-1 bg-gray-900 border border-gray-800 rounded-lg p-6">
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
              <p className="text-gray-400">Loading findings...</p>
            ) : findings.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-8 text-gray-500 border border-dashed border-gray-700 rounded bg-gray-950/50">
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
                        ? 'bg-gray-800 border-gray-600'
                        : 'bg-gray-950 border-gray-800 hover:border-gray-700'
                    }`}
                  >
                    <div className="flex items-center gap-4 flex-1 min-w-0">
                      <span className={`px-2.5 py-1 rounded text-xs font-medium border uppercase w-24 text-center shrink-0 ${getSeverityColor(finding.severity)}`}>
                        {finding.severity}
                      </span>
                      <div className="truncate">
                        <p className="text-white font-medium truncate">{finding.title}</p>
                        <p className="text-xs text-gray-400 mt-0.5">
                          Risk: <span className={getRiskColor(finding.risk_level)}>{finding.risk_level?.toUpperCase() || 'N/A'}</span> ({finding.risk_score?.toFixed(2) || '-'})
                        </p>
                      </div>
                    </div>
                    <ChevronRight size={18} className="text-gray-600 shrink-0 ml-2" />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Right: Detail Panel */}
          {selectedFinding && (
            <div className="flex-1 bg-gray-900 border border-gray-800 rounded-lg p-6 flex flex-col h-full max-h-[800px] overflow-y-auto">
              <div className="flex items-start justify-between mb-4 border-b border-gray-800 pb-4">
                <div>
                  <h2 className="text-2xl font-bold text-white mb-2">{selectedFinding.title}</h2>
                  <div className="flex flex-wrap gap-2 text-xs">
                    <span className={`px-2 py-1 rounded border ${getSeverityColor(selectedFinding.severity)}`}>
                      Severity: {selectedFinding.severity.toUpperCase()}
                    </span>
                    <span className={`px-2 py-1 rounded border bg-gray-800 border-gray-700 text-gray-300`}>
                      Confidence: {selectedFinding.confidence?.toUpperCase() || 'N/A'}
                    </span>
                    <span className={`px-2 py-1 rounded border bg-gray-800 border-gray-700 text-gray-300`}>
                      Status: {selectedFinding.status.toUpperCase()}
                    </span>
                  </div>
                </div>
              </div>

              <div className="space-y-6 text-sm text-gray-300">
                {/* Risk Panel */}
                <div className="bg-gray-950 border border-gray-800 rounded p-4">
                  <h4 className="font-semibold text-white mb-2 flex items-center gap-2">
                    <Shield size={16} className={getRiskColor(selectedFinding.risk_level)} />
                    Risk Assessment
                  </h4>
                  <div className="grid grid-cols-2 gap-4 mb-2">
                    <div>
                      <p className="text-gray-500">Risk Level</p>
                      <p className={`font-medium ${getRiskColor(selectedFinding.risk_level)}`}>
                        {selectedFinding.risk_level?.toUpperCase() || 'Unknown'}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500">Risk Score</p>
                      <p className="font-medium text-white">{selectedFinding.risk_score?.toFixed(2) || 'N/A'}</p>
                    </div>
                  </div>
                  {selectedFinding.risk_rationale && (
                    <div className="bg-gray-900 p-2 rounded text-xs text-gray-400 mt-2">
                      {selectedFinding.risk_rationale}
                    </div>
                  )}
                </div>

                <div>
                  <h4 className="font-semibold text-white mb-1">Description</h4>
                  <p className="whitespace-pre-wrap text-gray-400">
                    {selectedFinding.description || 'No description provided.'}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  {selectedFinding.category && (
                    <div>
                      <h4 className="font-semibold text-white mb-1">Category</h4>
                      <p className="text-gray-400">{selectedFinding.category}</p>
                    </div>
                  )}
                  {selectedFinding.location && (
                    <div>
                      <h4 className="font-semibold text-white mb-1">Location</h4>
                      <p className="text-gray-400">{selectedFinding.location}</p>
                    </div>
                  )}
                </div>

                {selectedFinding.impact && (
                  <div>
                    <h4 className="font-semibold text-white mb-1">Impact</h4>
                    <p className="whitespace-pre-wrap text-gray-400">{selectedFinding.impact}</p>
                  </div>
                )}
                
                {selectedFinding.remediation && (
                  <div>
                    <h4 className="font-semibold text-white mb-1">Remediation</h4>
                    <p className="whitespace-pre-wrap text-gray-400">{selectedFinding.remediation}</p>
                  </div>
                )}

                {/* Evidence Section */}
                <div className="pt-4 border-t border-gray-800">
                  <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
                    <FileText size={16} /> Evidence
                  </h4>
                  {loadingEvidence ? (
                    <p className="text-gray-500 italic">Loading evidence...</p>
                  ) : evidenceList.length === 0 ? (
                    <p className="text-gray-500 italic">No evidence items attached.</p>
                  ) : (
                    <div className="space-y-3">
                      {evidenceList.map(ev => (
                        <div key={ev.id} className="bg-gray-950 border border-gray-800 rounded overflow-hidden">
                          <div className="bg-gray-900 border-b border-gray-800 px-3 py-2 flex justify-between items-center text-xs">
                            <span className="font-medium text-gray-300">{ev.title || 'Evidence Item'}</span>
                            <span className="text-gray-500 uppercase px-1.5 py-0.5 rounded border border-gray-700 bg-gray-950">
                              {ev.evidence_type}
                            </span>
                          </div>
                          {ev.content && (
                            <div className="p-3">
                              <pre className="text-[11px] text-gray-400 font-mono whitespace-pre-wrap break-all bg-black p-2 rounded">
                                {ev.content}
                              </pre>
                            </div>
                          )}
                          {ev.source && (
                            <div className="px-3 pb-2 text-xs text-gray-600">
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
