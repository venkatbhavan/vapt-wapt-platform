import { useState, useEffect } from 'react';
import { 
  ArrowLeft, Shield, Activity, Crosshair,
  FileText, CheckCircle, Network, Wrench, ShieldAlert, Cpu, } from 'lucide-react';
import { DigitalThreatGlobe } from './visualizations/DigitalThreatGlobe';
import { SecurityGauge } from './visualizations/SecurityGauge';
import { TelemetryStrip } from './visualizations/TelemetryStrip';
import { ThreatFeed } from './visualizations/ThreatFeed';

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
                            } else {  }
        
      } catch (err: any) { setError(err.message); }
      finally { setLoading(false); }
    };
    fetchData();
  }, [assessmentId]);

  if (loading) return <div className="flex justify-center p-12"><div className="w-12 h-12 border-4 border-cyber-accent border-t-transparent rounded-full animate-spin"></div></div>;
  if (error || !assessment) return <div className="p-6 bg-red-900/20 text-red-400 border border-red-500/50 rounded">{error}</div>;

  const isScanning = summary?.scan_job_counts.running ? summary.scan_job_counts.running > 0 : false;

  
  return (
    <div className="space-y-6 animate-fade-in-up">
      <div className="flex justify-between items-center mb-2">
        <button 
          onClick={onBack}
          className="flex items-center gap-2 text-cyber-text hover:text-cyber-accent transition-colors font-mono text-sm uppercase tracking-wider"
        >
          <ArrowLeft size={16} /> BACK
        </button>
        <div className="flex gap-2">
          <button onClick={onViewAIAnalyst} className="bg-cyber-accent/10 border border-cyber-accent text-cyber-accent hover:bg-cyber-accent hover:text-black font-mono tracking-widest uppercase text-xs px-4 py-2 rounded flex items-center gap-2 transition-colors shadow-[0_0_10px_rgba(0,240,255,0.2)]">
            <Cpu size={14} /> AI Analyst
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-500/50 text-red-500 p-4 rounded flex items-center gap-3 font-mono text-sm">
          <ShieldAlert size={18} />
          <p>{error}</p>
        </div>
      )}

      {/* Telemetry Strip */}
      <TelemetryStrip 
        assets={(summary as any)?.total_assets || "--" || 0}
        services={(summary as any)?.total_services || "--" || 0}
        findings={summary?.total_findings || 0}
        risk={(summary as any)?.posture_score || 78 !== null ? (summary as any)?.posture_score || 78 : '--'}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Main Globe & Posture Panel */}
        <div className="lg:col-span-2 bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col relative h-[420px]">
          <div className="absolute top-0 left-0 w-full h-1 bg-cyber-accent"></div>
          <div className="bg-cyber-darkest/80 border-b border-cyber-border p-3 flex justify-between items-center z-10 backdrop-blur-sm absolute w-full top-0">
            <div className="flex items-center gap-2">
              <Shield size={16} className="text-cyber-accent" />
              <h3 className="font-mono text-white tracking-widest uppercase text-xs">Global Threat Map</h3>
            </div>
            {isScanning && (
              <span className="flex items-center gap-2 text-[10px] font-mono text-cyber-accent uppercase tracking-widest bg-cyber-accent/10 px-2 py-0.5 rounded border border-cyber-accent/30 animate-pulse">
                <Activity size={10} /> Active Scan
              </span>
            )}
          </div>
          
          <div className="flex-1 flex items-center justify-center relative overflow-hidden bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-cyber-darkest via-black to-black mt-10">
            <DigitalThreatGlobe />
            
            {/* Identity Overlay */}
            <div className="absolute top-4 left-4 bg-cyber-darkest/50 p-3 border border-cyber-border/50 rounded backdrop-blur">
              <p className="text-[10px] font-mono text-cyber-text uppercase tracking-widest mb-1">Assessment Target</p>
              <h2 className="text-lg font-bold text-white font-mono uppercase tracking-wider">{assessment?.name}</h2>
              <p className="text-cyber-accent font-mono text-xs">{assessment?.target}</p>
            </div>
            
            {/* Posture Overlay */}
            <div className="absolute top-4 right-4 bg-cyber-darkest/50 p-2 border border-cyber-border/50 rounded backdrop-blur">
              <SecurityGauge score={(summary as any)?.posture_score || 78 || 0} label="SYS POSTURE" />
            </div>
          </div>
        </div>

        {/* Threat Feed */}
        <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col h-[420px]">
          <div className="bg-cyber-darkest border-b border-cyber-border p-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity size={16} className="text-red-500" />
              <h3 className="font-mono text-white tracking-widest uppercase text-xs">Threat Feed</h3>
            </div>
            <span className="text-[10px] text-cyber-text font-mono uppercase tracking-widest">{recentFindings.length} EVENTS</span>
          </div>
          <div className="flex-1 overflow-y-auto p-3">
             <ThreatFeed events={recentFindings.map(f => ({
               id: String(f.id),
               severity: f.risk_level || 'INFO',
               title: f.title,
               timestamp: new Date().toLocaleTimeString() // simulate recent
             }))} />
          </div>
        </div>
      </div>

      {/* Module Links */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div onClick={() => onViewFindings()} className="group bg-cyber-darker border border-cyber-border hover:border-cyber-accent rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-4 cursor-pointer transition-colors flex flex-col items-center text-center">
            <Crosshair size={24} className="text-cyber-accent/70 group-hover:text-cyber-accent mb-2" />
            <span className="font-mono text-white text-xs uppercase tracking-widest">Findings</span>
          </div>
          <div onClick={() => onViewAttackSurface()} className="group bg-cyber-darker border border-cyber-border hover:border-cyber-accent rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-4 cursor-pointer transition-colors flex flex-col items-center text-center">
            <Network size={24} className="text-cyber-accent/70 group-hover:text-cyber-accent mb-2" />
            <span className="font-mono text-white text-xs uppercase tracking-widest">Topology</span>
          </div>
          <div onClick={() => onViewCompliance()} className="group bg-cyber-darker border border-cyber-border hover:border-cyber-accent rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-4 cursor-pointer transition-colors flex flex-col items-center text-center">
            <CheckCircle size={24} className="text-cyber-accent/70 group-hover:text-cyber-accent mb-2" />
            <span className="font-mono text-white text-xs uppercase tracking-widest">Compliance</span>
          </div>
          <div onClick={() => onViewRemediation()} className="group bg-cyber-darker border border-cyber-border hover:border-cyber-accent rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-4 cursor-pointer transition-colors flex flex-col items-center text-center">
            <Wrench size={24} className="text-cyber-accent/70 group-hover:text-cyber-accent mb-2" />
            <span className="font-mono text-white text-xs uppercase tracking-widest">Remediate</span>
          </div>
          <div onClick={() => onViewReports()} className="group bg-cyber-darker border border-cyber-border hover:border-cyber-accent rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-4 cursor-pointer transition-colors flex flex-col items-center text-center">
            <FileText size={24} className="text-cyber-accent/70 group-hover:text-cyber-accent mb-2" />
            <span className="font-mono text-white text-xs uppercase tracking-widest">Reports</span>
          </div>
          <div onClick={() => onViewPosture()} className="group bg-cyber-darker border border-cyber-border hover:border-cyber-accent rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-4 cursor-pointer transition-colors flex flex-col items-center text-center">
            <Shield size={24} className="text-cyber-accent/70 group-hover:text-cyber-accent mb-2" />
            <span className="font-mono text-white text-xs uppercase tracking-widest">Posture</span>
          </div>
      </div>

    </div>
  );
}
