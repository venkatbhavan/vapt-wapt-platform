import { useState, useEffect } from 'react';
import { ArrowLeft, AlertTriangle, Shield, CheckCircle, Activity, BarChart2 } from 'lucide-react';

interface Assessment {
  id: number;
  project_id: number;
  name: string;
  target: string;
  authorization_confirmed: boolean;
  scan_profile: string;
  scope: string;
  status: string;
  created_at: string;
}

interface SeverityCounts {
  critical: int;
  high: int;
  medium: int;
  low: int;
  info: int;
}

type int = number;

interface RiskCounts {
  critical: int;
  high: int;
  medium: int;
  low: int;
  info: int;
}

interface StatusCounts {
  open: int;
  accepted: int;
  false_positive: int;
  resolved: int;
}

interface ScanJobCounts {
  queued: int;
  running: int;
  completed: int;
  failed: int;
  cancelled: int;
}

interface AssessmentSummary {
  assessment_id: number;
  total_findings: number;
  severity_counts: SeverityCounts;
  risk_counts: RiskCounts;
  status_counts: StatusCounts;
  scan_job_counts: ScanJobCounts;
}

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

interface AssessmentDashboardProps {
  assessmentId: number;
  onBack: () => void;
  onViewFindings: (jobId?: number, findingId?: number) => void;
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

const getRiskBgColor = (riskLevel: string) => {
  switch (riskLevel.toLowerCase()) {
    case 'critical': return 'bg-purple-500';
    case 'high': return 'bg-red-500';
    case 'medium': return 'bg-orange-500';
    case 'low': return 'bg-yellow-500';
    case 'info': return 'bg-blue-500';
    default: return 'bg-gray-500';
  }
};

export function AssessmentDashboard({ assessmentId, onBack, onViewFindings }: AssessmentDashboardProps) {
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [summary, setSummary] = useState<AssessmentSummary | null>(null);
  const [recentFindings, setRecentFindings] = useState<Finding[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError('');
      try {
        // Fetch Assessment Details
        const assessRes = await fetch(`http://localhost:8000/api/assessments/${assessmentId}`);
        if (!assessRes.ok) {
            if (assessRes.status === 404) throw new Error('Assessment not found');
            throw new Error('Failed to fetch assessment');
        }
        const assessData: Assessment = await assessRes.json();
        setAssessment(assessData);

        // Fetch Summary
        const sumRes = await fetch(`http://localhost:8000/api/assessments/${assessmentId}/summary`);
        if (!sumRes.ok) throw new Error('Failed to fetch assessment summary');
        const sumData: AssessmentSummary = await sumRes.json();
        setSummary(sumData);

        // Fetch Recent Findings
        const jobsRes = await fetch(`http://localhost:8000/api/assessments/${assessmentId}/scan-jobs`);
        if (jobsRes.ok) {
            const jobsData: ScanJob[] = await jobsRes.json();
            const completedJobs = jobsData.filter(j => j.status === 'completed')
                .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
            
            if (completedJobs.length > 0) {
                const recentJob = completedJobs[0];
                const findingsRes = await fetch(`http://localhost:8000/api/scan-jobs/${recentJob.id}/findings`);
                if (findingsRes.ok) {
                    const findingsData: Finding[] = await findingsRes.json();
                    setRecentFindings(findingsData.slice(0, 5));
                }
            }
        }
      } catch (err: unknown) {
        if (err instanceof Error) {
            setError(err.message || 'API error');
        } else {
            setError('API error');
        }
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [assessmentId]);

  if (loading) {
      return <div className="text-gray-400 p-8 flex gap-3 items-center"><Activity className="animate-spin" size={20} /> Loading dashboard...</div>;
  }

  if (error || !assessment || !summary) {
      return (
          <div className="space-y-6">
            <button onClick={onBack} className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors">
              <ArrowLeft size={16} /> Back to Assessments
            </button>
            <div className="bg-red-500/10 border border-red-500 text-red-500 p-4 rounded-lg flex items-center gap-3">
              <AlertTriangle size={20} />
              <p>{error || 'Failed to load dashboard'}</p>
            </div>
          </div>
      );
  }

  const { total_findings } = summary;

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
          onClick={() => onViewFindings()}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded transition-colors"
        >
          <Activity size={16} />
          View Full Findings
        </button>
      </div>

      {/* Assessment Info Header */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6 flex flex-col md:flex-row justify-between md:items-start gap-4">
        <div>
            <h2 className="text-2xl font-bold text-white mb-2">{assessment.name}</h2>
            <p className="text-gray-400 text-sm mb-4">{assessment.scope}</p>
            <div className="flex flex-wrap gap-4 text-sm">
                <div>
                    <span className="text-gray-500 block text-xs">Target</span>
                    <span className="text-blue-400">{assessment.target}</span>
                </div>
                <div>
                    <span className="text-gray-500 block text-xs">Scan Profile</span>
                    <span className="text-gray-300 uppercase">{assessment.scan_profile}</span>
                </div>
                <div>
                    <span className="text-gray-500 block text-xs">Authorization</span>
                    {assessment.authorization_confirmed ? (
                        <span className="text-green-400">Confirmed</span>
                    ) : (
                        <span className="text-red-400">Missing</span>
                    )}
                </div>
            </div>
        </div>
        <div className="bg-gray-950 border border-gray-800 p-4 rounded-lg min-w-[150px] text-center shrink-0">
            <span className="text-gray-400 text-xs uppercase block mb-1">Total Findings</span>
            <span className="text-4xl font-bold text-white">{total_findings}</span>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-gray-900 border border-purple-500/30 p-4 rounded-lg flex flex-col items-center justify-center">
            <span className="text-purple-400 text-xs uppercase font-bold mb-1">CRITICAL</span>
            <span className="text-3xl font-bold text-white">{summary.severity_counts.critical}</span>
        </div>
        <div className="bg-gray-900 border border-red-500/30 p-4 rounded-lg flex flex-col items-center justify-center">
            <span className="text-red-400 text-xs uppercase font-bold mb-1">HIGH</span>
            <span className="text-3xl font-bold text-white">{summary.severity_counts.high}</span>
        </div>
        <div className="bg-gray-900 border border-orange-500/30 p-4 rounded-lg flex flex-col items-center justify-center">
            <span className="text-orange-400 text-xs uppercase font-bold mb-1">MEDIUM</span>
            <span className="text-3xl font-bold text-white">{summary.severity_counts.medium}</span>
        </div>
        <div className="bg-gray-900 border border-yellow-500/30 p-4 rounded-lg flex flex-col items-center justify-center">
            <span className="text-yellow-400 text-xs uppercase font-bold mb-1">LOW</span>
            <span className="text-3xl font-bold text-white">{summary.severity_counts.low}</span>
        </div>
        <div className="bg-gray-900 border border-blue-500/30 p-4 rounded-lg flex flex-col items-center justify-center">
            <span className="text-blue-400 text-xs uppercase font-bold mb-1">INFO</span>
            <span className="text-3xl font-bold text-white">{summary.severity_counts.info}</span>
        </div>
      </div>

      {/* Main Stats Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Risk Distribution */}
        <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-lg p-6">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <BarChart2 size={18} className="text-blue-500" />
                Risk Distribution
            </h3>
            {total_findings === 0 ? (
                <div className="py-8 text-center text-gray-500">No findings to display risk distribution</div>
            ) : (
                <div className="space-y-4 mt-2">
                    {['critical', 'high', 'medium', 'low', 'info'].map((level) => {
                        const count = summary.risk_counts[level as keyof RiskCounts] as number;
                        const pct = Math.max(0, Math.min(100, (count / total_findings) * 100));
                        return (
                            <div key={level}>
                                <div className="flex justify-between text-xs mb-1">
                                    <span className="uppercase text-gray-400 font-medium">{level}</span>
                                    <span className="text-white font-mono">{count} ({pct.toFixed(1)}%)</span>
                                </div>
                                <div className="w-full bg-gray-950 rounded-full h-2.5">
                                    <div className={`${getRiskBgColor(level)} h-2.5 rounded-full`} style={{ width: `${pct}%` }}></div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>

        {/* Statuses */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6 space-y-6">
            <div>
                <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">Finding Status</h3>
                <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                        <span className="text-gray-300">Open</span>
                        <span className="text-white font-mono bg-gray-800 px-2 rounded">{summary.status_counts.open}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-300">Accepted</span>
                        <span className="text-white font-mono bg-gray-800 px-2 rounded">{summary.status_counts.accepted}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-300">False Positive</span>
                        <span className="text-white font-mono bg-gray-800 px-2 rounded">{summary.status_counts.false_positive}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-300">Resolved</span>
                        <span className="text-white font-mono bg-gray-800 px-2 rounded">{summary.status_counts.resolved}</span>
                    </div>
                </div>
            </div>

            <div className="pt-6 border-t border-gray-800">
                <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">Scan Jobs</h3>
                <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                        <span className="text-gray-300">Completed</span>
                        <span className="text-green-400 font-mono bg-green-500/10 px-2 rounded">{summary.scan_job_counts.completed}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-300">Running</span>
                        <span className="text-blue-400 font-mono bg-blue-500/10 px-2 rounded">{summary.scan_job_counts.running}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-300">Queued</span>
                        <span className="text-yellow-400 font-mono bg-yellow-500/10 px-2 rounded">{summary.scan_job_counts.queued}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-300">Failed</span>
                        <span className="text-red-400 font-mono bg-red-500/10 px-2 rounded">{summary.scan_job_counts.failed}</span>
                    </div>
                </div>
            </div>
        </div>
      </div>

      {/* Recent Findings */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <Shield size={18} className="text-blue-500" />
            Recent Findings
        </h3>
        {recentFindings.length === 0 ? (
            <div className="py-8 text-center border border-dashed border-gray-700 rounded bg-gray-950 flex flex-col items-center">
                <CheckCircle size={32} className="mb-2 text-green-500/50" />
                <p className="text-gray-500">No recent findings reported.</p>
            </div>
        ) : (
            <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase tracking-wider">
                            <th className="pb-3 pr-4 font-medium">Severity</th>
                            <th className="pb-3 pr-4 font-medium">Title</th>
                            <th className="pb-3 pr-4 font-medium">Risk Level</th>
                            <th className="pb-3 font-medium">Status</th>
                        </tr>
                    </thead>
                    <tbody className="text-sm">
                        {recentFindings.map(f => (
                            <tr 
                                key={f.id} 
                                onClick={() => onViewFindings(f.scan_job_id, f.id)}
                                className="border-b border-gray-800/50 hover:bg-gray-800/50 cursor-pointer transition-colors group"
                            >
                                <td className="py-3 pr-4">
                                    <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase ${getSeverityColor(f.severity)}`}>
                                        {f.severity}
                                    </span>
                                </td>
                                <td className="py-3 pr-4 font-medium text-white group-hover:text-blue-400 transition-colors">
                                    {f.title}
                                </td>
                                <td className="py-3 pr-4">
                                    <span className={getRiskColor(f.risk_level)}>
                                        {f.risk_level?.toUpperCase() || 'N/A'}
                                    </span>
                                </td>
                                <td className="py-3">
                                    <span className="text-gray-300 uppercase text-xs">
                                        {f.status}
                                    </span>
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
