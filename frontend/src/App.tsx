import { useState, useEffect } from 'react';
import { Shield, Activity, Database, ShieldAlert } from 'lucide-react';
import { ProjectsView } from './components/ProjectsView';
import { AssessmentsView } from './components/AssessmentsView';
import { AssessmentDashboard } from './components/AssessmentDashboard';
import { FindingsView } from './components/FindingsView';
import { AttackSurfaceView } from './components/AttackSurfaceView';
import { ComplianceView } from './components/ComplianceView';
import { RemediationView } from './components/RemediationView';
import { RetestView } from './components/RetestView';
import { ReportsView } from './components/ReportsView';
import { AIAnalystView } from './components/AIAnalystView';
import { PostureView } from './components/PostureView';
import { SharedReportView } from './components/SharedReportView';

function App() {
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [selectedAssessmentId, setSelectedAssessmentId] = useState<number | null>(null);
  const [viewingFindings, setViewingFindings] = useState<{jobId?: number | null, findingId?: number | null} | false>(false);
  const [viewingAttackSurface, setViewingAttackSurface] = useState(false);
  const [viewingCompliance, setViewingCompliance] = useState(false);
  const [viewingRemediation, setViewingRemediation] = useState(false);
  const [viewingRetests, setViewingRetests] = useState(false);
  const [viewingReports, setViewingReports] = useState(false);
  const [viewingAIAnalyst, setViewingAIAnalyst] = useState(false);
  const [viewingPosture, setViewingPosture] = useState(false);
  
  const [apiStatus, setApiStatus] = useState<'Checking' | 'Connected' | 'Disconnected' | 'Error'>('Checking');

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/health`)
      .then(res => res.json())
      .then(data => setApiStatus(data.status === 'ok' ? 'Connected' : 'Error'))
      .catch(() => setApiStatus('Disconnected'));
  }, []);

  const path = window.location.pathname;
  if (path.startsWith('/shared/reports/')) {
    return <SharedReportView />;
  }

  return (
    <div className="min-h-screen bg-cyber-darkest bg-grid-pattern relative text-cyber-textBright p-8 font-sans">
      <header className="flex justify-between items-center mb-8 pb-4 border-b border-cyber-border">
        <div className="flex items-center gap-4">
          <div className="p-2 bg-cyber-accent/10 border border-cyber-accent/30 rounded">
            <Shield className="text-cyber-accent" size={28} />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-widest text-white font-mono uppercase">VAPT Command Center</h1>
            <p className="text-cyber-accent text-xs font-mono uppercase tracking-widest mt-1">Security Operations & Intelligence</p>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex flex-col items-end">
            <span className="text-xs font-mono text-cyber-text uppercase tracking-widest mb-1">System Status</span>
            <div className="flex items-center gap-2 bg-cyber-darker border border-cyber-border px-3 py-1.5 rounded">
              <div className={`w-2 h-2 rounded-full ${apiStatus === 'Connected' ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
              <span className={`text-xs font-mono tracking-widest uppercase ${apiStatus === 'Connected' ? 'text-green-500' : 'text-red-500'}`}>
                {apiStatus === 'Connected' ? 'TELEMETRY ONLINE' : 'CONNECTION LOST'}
              </span>
            </div>
          </div>
        </div>
      </header>

      {import.meta.env.VITE_DEMO_MODE === 'true' && (
        <div className="mb-8 border border-cyber-accent bg-cyber-darker p-4 rounded flex flex-col gap-1 max-w-xl shadow-[0_0_15px_rgba(0,255,255,0.15)] relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-cyber-accent"></div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-cyber-accent animate-pulse"></div>
            <h2 className="text-cyber-accent font-bold tracking-wider text-sm uppercase font-mono">DEMO MODE — READ ONLY</h2>
          </div>
          <p className="text-cyber-text text-sm ml-4 font-mono uppercase">Simulated security assessment. Scanner execution is disabled.</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <div className="bg-cyber-darker relative overflow-hidden group hover:border-cyber-accent transition-colors duration-300 border border-cyber-border p-5 rounded shadow-[0_0_15px_rgba(0,0,0,0.5)]">
          <div className="absolute top-0 left-0 w-1 h-full bg-cyber-accent/50 group-hover:bg-cyber-accent transition-colors"></div>
          <div className="flex justify-between items-start mb-2 ml-2">
            <div>
              <p className="text-xs font-mono text-cyber-accent uppercase tracking-widest">Active Operations</p>
              <h2 className="text-2xl font-bold text-white mt-1 font-mono">--</h2>
            </div>
            <Activity className="text-cyber-accent/70" size={20} />
          </div>
        </div>

        <div className="bg-cyber-darker relative overflow-hidden group hover:border-cyber-accent transition-colors duration-300 border border-cyber-border p-5 rounded shadow-[0_0_15px_rgba(0,0,0,0.5)]">
          <div className="absolute top-0 left-0 w-1 h-full bg-cyber-border group-hover:bg-cyber-accent transition-colors"></div>
          <div className="flex justify-between items-start mb-2 ml-2">
            <div>
              <p className="text-xs font-mono text-cyber-accent uppercase tracking-widest">Active Workspaces</p>
              <h2 className="text-2xl font-bold text-white mt-1 font-mono">--</h2>
            </div>
            <Database className="text-cyber-text/70" size={20} />
          </div>
        </div>

        <div className="bg-cyber-darker relative overflow-hidden group hover:border-red-500/50 transition-colors duration-300 border border-cyber-border p-5 rounded shadow-[0_0_15px_rgba(0,0,0,0.5)]">
          <div className="absolute top-0 left-0 w-1 h-full bg-red-900/50 group-hover:bg-red-500 transition-colors"></div>
          <div className="flex justify-between items-start mb-2 ml-2">
            <div>
              <p className="text-xs font-mono text-red-500 uppercase tracking-widest">Critical Threats</p>
              <h2 className="text-2xl font-bold text-red-500 mt-1 font-mono">--</h2>
            </div>
            <ShieldAlert className="text-red-500/70" size={20} />
          </div>
        </div>
      </div>

      <div className="w-full">
        {selectedAssessmentId ? (
          viewingAttackSurface ? (
            <AttackSurfaceView
              assessmentId={selectedAssessmentId}
              onBack={() => setViewingAttackSurface(false)}
              onViewFinding={(findingId) => {
                setViewingAttackSurface(false);
                setViewingFindings({findingId});
              }}
            />
          ) : viewingCompliance ? (
            <ComplianceView
              assessmentId={selectedAssessmentId}
              onBack={() => setViewingCompliance(false)}
              onViewFinding={(findingId) => {
                setViewingCompliance(false);
                setViewingFindings({findingId});
              }}
            />
          ) : viewingRemediation ? (
            <RemediationView
              assessmentId={selectedAssessmentId}
              onBack={() => setViewingRemediation(false)}
              onViewFinding={(findingId) => {
                setViewingRemediation(false);
                setViewingRetests(false);
                setViewingReports(false);
                setViewingPosture(false);
                setViewingAIAnalyst(false);
                setViewingFindings({findingId});
              }}
            />
          ) : viewingRetests ? (
            <RetestView
              assessmentId={selectedAssessmentId}
              onBack={() => setViewingRetests(false)}
              onViewFinding={(findingId) => {
                setViewingRetests(false);
                setViewingReports(false);
                setViewingPosture(false);
                setViewingAIAnalyst(false);
                setViewingFindings({findingId});
              }}
            />
          ) : viewingPosture ? (
            <PostureView
              assessmentId={selectedAssessmentId}
              onBack={() => setViewingPosture(false)}
            />
          ) : viewingAIAnalyst ? (
            <AIAnalystView
              assessmentId={selectedAssessmentId}
              onBack={() => setViewingAIAnalyst(false)}
            />
          ) : viewingReports ? (
            <ReportsView
              assessmentId={selectedAssessmentId}
              onBack={() => setViewingReports(false)}
            />
          ) : viewingFindings ? (
            <FindingsView
              assessmentId={selectedAssessmentId}
              initialJobId={viewingFindings.jobId}
              initialFindingId={viewingFindings.findingId}
              onBack={() => setViewingFindings(false)}
            />
          ) : (
            <AssessmentDashboard
              assessmentId={selectedAssessmentId}
              onBack={() => {
                setSelectedAssessmentId(null);
                setViewingFindings(false);
                setViewingAttackSurface(false);
                setViewingCompliance(false);
                setViewingRemediation(false);
                setViewingRetests(false);
                setViewingReports(false);
                setViewingPosture(false);
                setViewingAIAnalyst(false);
              }}
              onViewFindings={(jobId, findingId) => setViewingFindings({jobId, findingId})}
              onViewAttackSurface={() => setViewingAttackSurface(true)}
              onViewCompliance={() => setViewingCompliance(true)}
              onViewRemediation={() => setViewingRemediation(true)}
              onViewRetests={() => setViewingRetests(true)}
              onViewReports={() => setViewingReports(true)}
              onViewPosture={() => setViewingPosture(true)}
              onViewAIAnalyst={() => setViewingAIAnalyst(true)}
            />
          )
        ) : selectedProjectId ? (
          <AssessmentsView
            projectId={selectedProjectId}
            onBack={() => setSelectedProjectId(null)}
            onSelectAssessment={setSelectedAssessmentId}
          />
        ) : (
          <ProjectsView onSelectProject={setSelectedProjectId} />
        )}
      </div>

    </div>
  );
}

export default App;
