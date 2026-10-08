import { useState, useEffect } from 'react';
import { ArrowLeft, AlertTriangle, Activity, ClipboardCheck, Wrench, ShieldCheck, FileText, BrainCircuit, Target, Server, Network } from 'lucide-react';
import { RadarVisualization } from './RadarVisualization';

interface Assessment {
  id: number; project_id: number; name: string; target: string; authorization_confirmed: boolean;
  scan_profile: string; scope: string; status: string; created_at: string;
}
interface SeverityCounts { critical: number; high: number; medium: number; low: number; info: number; }
interface RiskCounts { critical: number; high: number; medium: number; low: number; info: number; }
interface StatusCounts { open: number; accepted: number; false_positive: number; resolved: number; }
interface ScanJobCounts { queued: number; running: number; completed: number; failed: number; cancelled: number; }
interface AssessmentSummary {
  assessment_id: number; total_findings: number;
  severity_counts: SeverityCounts; risk_counts: RiskCounts;
  status_counts: StatusCounts; scan_job_counts: ScanJobCounts;
}
// interface ScanJob {
  // id: number; assessment_id: number; scan_profile: string; status: string;
  // created_at: string; started_at: string | null; completed_at: string | null; error_message: string | null;
// }
interface Finding {
  id: number; scan_job_id: number; title: string; description: string;
  severity: string; confidence: string; category: string; location: string;
  impact: string; remediation: string; status: string; risk_score: number | null;
  risk_level: string | null; risk_rationale: string | null; created_at: string; updated_at: string;
}
interface AssessmentDashboardProps {
  assessmentId: number; onBack: () => void; onViewFindings: (jobId?: number, findingId?: number) => void;
  onViewAttackSurface: () => void; onViewCompliance: () => void; onViewRemediation: () => void;
  onViewRetests: () => void; onViewReports: () => void; onViewPosture: () => void; onViewAIAnalyst: () => void;
}

// @ts-ignore
export function AssessmentDashboard({ assessmentId, onBack, onViewFindings, onViewAttackSurface, onViewCompliance, onViewRemediation, onViewRetests, onViewReports, onViewPosture, onViewAIAnalyst }: AssessmentDashboardProps) {
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [summary, setSummary] = useState<AssessmentSummary | null>(null);
  const [recentFindings, setRecentFindings] = useState<Finding[]>([]);
  const [postureScore, setPostureScore] = useState<number>(-1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true); setError('');
      try {
        const [assessRes, sumRes, findRes, postRes] = await Promise.all([
          fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/assessments/` + assessmentId),
          fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/assessments/` + assessmentId + '/summary'),
          fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/assessments/` + assessmentId + '/findings?limit=5'),
          fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/assessments/` + assessmentId + '/posture').catch(() => null)
        ]);
        
        if (!assessRes.ok) throw new Error('Assessment not found');
        setAssessment(await assessRes.json());
        
        if (sumRes.ok) setSummary(await sumRes.json());
        if (findRes.ok) { const fd = await findRes.json(); setRecentFindings(fd.items || []); }
        
        if (postRes && postRes.ok) {
          const postData = await postRes.json();
          setPostureScore(postData.score !== undefined && postData.score !== null ? postData.score : -1);
        } else { setPostureScore(-1); }
        
      } catch (err: any) { setError(err.message); }
      finally { setLoading(false); }
    };
    fetchData();
  }, [assessmentId]);

  if (loading) return <div className="flex justify-center p-12"><div className="w-12 h-12 border-4 border-cyber-accent border-t-transparent rounded-full animate-spin"></div></div>;
  if (error || !assessment) return <div className="p-6 bg-red-900/20 text-red-400 border border-red-500/50 rounded">{error}</div>;

  const isScanning = summary?.scan_job_counts.running ? summary.scan_job_counts.running > 0 : false;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="flex items-center gap-2 text-cyber-text hover:text-cyber-accent transition-colors font-mono uppercase text-sm tracking-wider">
          <ArrowLeft className="w-4 h-4" /> System Overview
        </button>
        <div className="flex gap-3">
          <button onClick={onViewPosture} className="border border-cyber-accent text-cyber-accent hover:bg-cyber-accent hover:text-black font-bold uppercase tracking-widest py-2 px-4 rounded transition-colors font-mono text-sm flex items-center gap-2">
            <ShieldCheck size={16} /> Security Posture
          </button>
          <button onClick={onViewAIAnalyst} className="bg-cyber-accent hover:bg-cyber-accent/80 text-black font-bold uppercase tracking-widest py-2 px-4 rounded transition-colors font-mono text-sm flex items-center gap-2">
            <BrainCircuit size={16} /> AI Analyst
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Core Radar View */}
        <div className="lg:col-span-1 bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden relative">
          <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
            <Target size={18} className="text-cyber-accent" />
            <h3 className="font-mono text-white tracking-widest uppercase text-sm">Target Radar</h3>
          </div>
          <div className="p-6 relative group hover:border-cyber-accent/30 transition-colors">
            <RadarVisualization score={postureScore} label="Security Score" />
            <div className="mt-8 text-center">
              <h2 className="text-2xl font-bold text-white tracking-wider">{assessment.name}</h2>
              <p className="text-cyber-accent font-mono text-sm mt-1">{assessment.target}</p>
            </div>
            {isScanning && (
              <div className="absolute top-4 right-4 flex items-center gap-2 bg-cyber-dark px-3 py-1 rounded border border-cyber-accent/50 text-cyber-accent font-mono text-xs animate-pulse">
                <Activity className="w-3 h-3" /> SCAN IN PROGRESS
              </div>
            )}
          </div>
        </div>

        {/* Action Center */}
        <div className="lg:col-span-2 grid grid-cols-2 gap-4">
          <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col justify-between">
             <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
               <AlertTriangle size={18} className="text-cyber-accent" />
               <h3 className="font-mono text-white tracking-widest uppercase text-sm">Critical Threats</h3>
             </div>
             <div className="p-4">
               <div className="text-4xl font-mono font-bold text-white">{summary?.risk_counts.critical || 0}</div>
               <button onClick={() => onViewFindings()} className="mt-4 text-xs font-mono text-cyber-accent uppercase hover:underline text-left tracking-wider">View Findings ?</button>
             </div>
          </div>

          <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col justify-between">
             <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
               <AlertTriangle size={18} className="text-cyber-accent" />
               <h3 className="font-mono text-white tracking-widest uppercase text-sm">High Risk</h3>
             </div>
             <div className="p-4">
               <div className="text-4xl font-mono font-bold text-white">{summary?.risk_counts.high || 0}</div>
               <button onClick={() => onViewFindings()} className="mt-4 text-xs font-mono text-cyber-accent uppercase hover:underline text-left tracking-wider">View Findings ?</button>
             </div>
          </div>

          <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col justify-between">
             <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
               <Network size={18} className="text-cyber-accent" />
               <h3 className="font-mono text-white tracking-widest uppercase text-sm">Attack Surface</h3>
             </div>
             <div className="p-4">
               <div className="text-4xl font-mono font-bold text-white">Map</div>
               <button onClick={() => onViewAttackSurface()} className="mt-4 text-xs font-mono text-cyber-accent uppercase hover:underline text-left tracking-wider">View Topology ?</button>
             </div>
          </div>

          <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col justify-between">
             <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
               <ClipboardCheck size={18} className="text-cyber-accent" />
               <h3 className="font-mono text-white tracking-widest uppercase text-sm">Compliance</h3>
             </div>
             <div className="p-4">
               <div className="text-4xl font-mono font-bold text-white">Matrix</div>
               <button onClick={() => onViewCompliance()} className="mt-4 text-xs font-mono text-cyber-accent uppercase hover:underline text-left tracking-wider">View Controls ?</button>
             </div>
          </div>
          
          <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col justify-between">
             <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
               <Wrench size={18} className="text-cyber-accent" />
               <h3 className="font-mono text-white tracking-widest uppercase text-sm">Remediation</h3>
             </div>
             <div className="p-4">
               <div className="text-4xl font-mono font-bold text-white">Plans</div>
               <button onClick={() => onViewRemediation()} className="mt-4 text-xs font-mono text-cyber-accent uppercase hover:underline text-left tracking-wider">View Actions ?</button>
             </div>
          </div>
          
          <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col justify-between">
             <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
               <FileText size={18} className="text-cyber-accent" />
               <h3 className="font-mono text-white tracking-widest uppercase text-sm">Reports</h3>
             </div>
             <div className="p-4">
               <div className="text-4xl font-mono font-bold text-white">Exports</div>
               <button onClick={() => onViewReports()} className="mt-4 text-xs font-mono text-cyber-accent uppercase hover:underline text-left tracking-wider">View Documents ?</button>
             </div>
          </div>

        </div>
      </div>
      
      {/* Recent Findings Threat Log */}
      <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
        <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
          <Server size={18} className="text-cyber-accent" />
          <h3 className="font-mono text-white tracking-widest uppercase text-sm">Threat Detection Log</h3>
        </div>
        <div className="p-4 space-y-2">
          {recentFindings.length === 0 ? (
            <div className="p-8 flex flex-col items-center justify-center text-center">
              <Server size={48} className="text-cyber-border mb-4" />
              <h4 className="text-white font-mono uppercase tracking-widest mb-2">No Threats Detected</h4>
              <p className="text-cyber-text font-mono text-sm">No recent threat activity found in this assessment.</p>
            </div>
          ) : (
            recentFindings.map(f => (
              <div key={f.id} className="flex items-center justify-between p-3 bg-cyber-dark border border-cyber-border rounded hover:border-cyber-accent/50 cursor-pointer transition-colors" onClick={() => onViewFindings(undefined, f.id)}>
                <div className="flex items-center gap-3">
                  <span className={`border px-2 py-0.5 rounded text-xs font-mono uppercase ${
                    f.risk_level?.toLowerCase() === 'critical' ? 'border-risk-critical text-risk-critical' :
                    f.risk_level?.toLowerCase() === 'high' ? 'border-risk-high text-risk-high' :
                    f.risk_level?.toLowerCase() === 'medium' ? 'border-risk-medium text-risk-medium' :
                    f.risk_level?.toLowerCase() === 'low' ? 'border-risk-low text-risk-low' : 'border-risk-info text-risk-info'
                  }`}>
                    {f.risk_level || 'INFO'}
                  </span>
                  <span className="font-mono text-sm text-white">{f.title}</span>
                </div>
                <div className="flex gap-4">
                  <span className="font-mono uppercase text-xs tracking-wider text-cyber-text">{f.location}</span>
                  <span className="font-mono text-xs text-cyber-accent">{f.risk_score ? f.risk_score.toFixed(1) : 'N/A'}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
