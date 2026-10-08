import { useState, useEffect } from 'react';
import { Plus, Terminal, Shield, AlertTriangle, ArrowRight, Activity, Crosshair, CheckCircle, Radio } from 'lucide-react';

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface Project {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

interface Assessment {
  id: number;
  status: string;
  scan_profile: string;
}

interface ProjectMeta {
  id: number;
  assessmentCount: number;
  hasActive: boolean;
  status: 'ACTIVE' | 'READY' | 'NO ASSESSMENT';
}

interface ProjectsViewProps {
  onSelectProject: (id: number) => void;
}

// Mini target reticle SVG — purely decorative, communicates "security environment"
function MiniReticle({ active = false }: { active?: boolean }) {
  return (
    <svg viewBox="0 0 60 60" className="w-10 h-10 flex-shrink-0" aria-hidden="true">
      <circle cx="30" cy="30" r="27" fill="none" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.3" />
      <circle cx="30" cy="30" r="18" fill="none" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.4" />
      <circle cx="30" cy="30" r="9" fill="none" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.6" />
      {/* crosshairs */}
      <line x1="30" y1="2" x2="30" y2="14" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.5" />
      <line x1="30" y1="46" x2="30" y2="58" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.5" />
      <line x1="2" y1="30" x2="14" y2="30" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.5" />
      <line x1="46" y1="30" x2="58" y2="30" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.5" />
      {/* center dot */}
      <circle cx="30" cy="30" r="2.5" fill="currentColor" opacity={active ? 1 : 0.5} />
      {active && (
        <circle cx="30" cy="30" r="5" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.6"
          className="animate-pulse" />
      )}
    </svg>
  );
}

// Animated target acquisition — beside the create form
function TargetAcquisition() {
  return (
    <div className="hidden xl:flex flex-col items-center justify-center w-48 flex-shrink-0" aria-hidden="true">
      <svg viewBox="0 0 120 120" className="w-40 h-40 text-cyber-accent">
        {/* outer ring — slow spin */}
        <circle cx="60" cy="60" r="55" fill="none" stroke="currentColor" strokeWidth="0.6" strokeOpacity="0.2"
          strokeDasharray="4 8" className="animate-radar" style={{ animationDuration: '20s' }} />
        {/* rings */}
        <circle cx="60" cy="60" r="44" fill="none" stroke="currentColor" strokeWidth="0.6" strokeOpacity="0.3" />
        <circle cx="60" cy="60" r="30" fill="none" stroke="currentColor" strokeWidth="0.6" strokeOpacity="0.4" />
        <circle cx="60" cy="60" r="16" fill="none" stroke="currentColor" strokeWidth="0.6" strokeOpacity="0.5" />
        {/* sweep */}
        <g className="animate-radar origin-center" style={{ transformOrigin: '60px 60px', animationDuration: '4s' }}>
          <path d="M60,60 L60,5" stroke="currentColor" strokeWidth="1" strokeOpacity="0.5" />
        </g>
        {/* crosshairs */}
        <line x1="60" y1="2" x2="60" y2="20" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.4" />
        <line x1="60" y1="100" x2="60" y2="118" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.4" />
        <line x1="2" y1="60" x2="20" y2="60" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.4" />
        <line x1="100" y1="60" x2="118" y2="60" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.4" />
        {/* corner brackets */}
        <path d="M10,20 L10,10 L20,10" fill="none" stroke="currentColor" strokeWidth="1.2" strokeOpacity="0.6" />
        <path d="M100,10 L110,10 L110,20" fill="none" stroke="currentColor" strokeWidth="1.2" strokeOpacity="0.6" />
        <path d="M10,100 L10,110 L20,110" fill="none" stroke="currentColor" strokeWidth="1.2" strokeOpacity="0.6" />
        <path d="M100,110 L110,110 L110,100" fill="none" stroke="currentColor" strokeWidth="1.2" strokeOpacity="0.6" />
        {/* node dots */}
        <circle cx="60" cy="16" r="2" fill="currentColor" opacity="0.6" className="animate-pulse" />
        <circle cx="60" cy="104" r="2" fill="currentColor" opacity="0.6" className="animate-pulse" style={{ animationDelay: '0.5s' }} />
        <circle cx="16" cy="60" r="2" fill="currentColor" opacity="0.6" className="animate-pulse" style={{ animationDelay: '1s' }} />
        <circle cx="104" cy="60" r="2" fill="currentColor" opacity="0.6" className="animate-pulse" style={{ animationDelay: '1.5s' }} />
        {/* center */}
        <circle cx="60" cy="60" r="3" fill="currentColor" opacity="0.9" />
      </svg>
      <p className="text-[9px] font-mono text-cyber-accent/60 uppercase tracking-widest mt-1 text-center">
        WORKSPACE<br />INITIALIZATION
      </p>
    </div>
  );
}

function StatusBadge({ status }: { status: 'ACTIVE' | 'READY' | 'NO ASSESSMENT' }) {
  if (status === 'ACTIVE') return (
    <span className="flex items-center gap-1 text-[9px] font-mono uppercase tracking-widest text-green-400 bg-green-500/10 border border-green-500/30 px-1.5 py-0.5 rounded">
      <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse inline-block"></span>ACTIVE
    </span>
  );
  if (status === 'NO ASSESSMENT') return (
    <span className="flex items-center gap-1 text-[9px] font-mono uppercase tracking-widest text-cyber-text bg-cyber-darkest border border-cyber-border px-1.5 py-0.5 rounded">
      <Radio size={8} />NO ASSESSMENT
    </span>
  );
  return (
    <span className="flex items-center gap-1 text-[9px] font-mono uppercase tracking-widest text-cyber-accent bg-cyber-accent/10 border border-cyber-accent/30 px-1.5 py-0.5 rounded">
      <CheckCircle size={8} />READY
    </span>
  );
}

export function ProjectsView({ onSelectProject }: ProjectsViewProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [meta, setMeta] = useState<Record<number, ProjectMeta>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [creating, setCreating] = useState(false);

  const fetchProjects = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API}/api/projects`);
      if (!res.ok) throw new Error('Failed to fetch projects');
      const data: Project[] = await res.json();
      setProjects(data);
      // Fetch assessment counts in parallel (best-effort — don't block render)
      const metaMap: Record<number, ProjectMeta> = {};
      await Promise.allSettled(
        data.map(async (p) => {
          try {
            const ar = await fetch(`${API}/api/projects/${p.id}/assessments`);
            const assessments: Assessment[] = ar.ok ? await ar.json() : [];
            const hasActive = assessments.some(a => a.status === 'running' || a.status === 'queued');
            metaMap[p.id] = {
              id: p.id,
              assessmentCount: assessments.length,
              hasActive,
              status: assessments.length === 0 ? 'NO ASSESSMENT' : hasActive ? 'ACTIVE' : 'READY',
            };
          } catch {
            metaMap[p.id] = { id: p.id, assessmentCount: 0, hasActive: false, status: 'NO ASSESSMENT' };
          }
        })
      );
      setMeta(metaMap);
    } catch (err: any) {
      setError(err.message || 'API unavailable');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchProjects(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name) return;
    setCreating(true);
    setError('');
    try {
      const res = await fetch(`${API}/api/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to create project');
      }
      setName('');
      setDescription('');
      await fetchProjects();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  // Aggregate telemetry from loaded meta
  const totalAssessments = Object.values(meta).reduce((s, m) => s + m.assessmentCount, 0);
  const activeWorkspaces = Object.values(meta).filter(m => m.status === 'ACTIVE').length;

  return (
    <div className="space-y-8">

      {/* ── WORKSPACE HEADER ── */}
      <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
        <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <Shield size={18} className="text-cyber-accent" />
            <h2 className="font-mono text-white tracking-widest uppercase text-sm">Active Security Workspaces</h2>
          </div>
          {!loading && (
            <div className="flex gap-4 flex-wrap">
              <div className="flex flex-col items-center border-r border-cyber-border pr-4">
                <span className="text-[10px] font-mono text-cyber-text uppercase tracking-widest">Workspaces</span>
                <span className="font-mono text-white text-lg font-bold">{projects.length}</span>
              </div>
              <div className="flex flex-col items-center border-r border-cyber-border pr-4">
                <span className="text-[10px] font-mono text-cyber-text uppercase tracking-widest">Online</span>
                <span className="font-mono text-green-400 text-lg font-bold">{activeWorkspaces}</span>
              </div>
              <div className="flex flex-col items-center">
                <span className="text-[10px] font-mono text-cyber-text uppercase tracking-widest">Assessments</span>
                <span className="font-mono text-cyber-accent text-lg font-bold">{totalAssessments}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── INITIALIZE WORKSPACE FORM ── */}
      <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
        <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
          <Terminal size={18} className="text-cyber-accent" />
          <div>
            <h3 className="font-mono text-white tracking-widest uppercase text-sm">Initialize Security Workspace</h3>
            <p className="font-mono text-cyber-text text-[10px] uppercase tracking-widest mt-0.5">
              Create an authorized security assessment environment
            </p>
          </div>
        </div>

        <div className="p-6 flex gap-8 items-start">
          <form onSubmit={handleCreate} className="flex-1 space-y-6 max-w-2xl">

            {/* IDENTITY */}
            <div>
              <p className="text-[10px] font-mono text-cyber-accent/70 uppercase tracking-widest border-b border-cyber-border pb-1 mb-4 flex items-center gap-2">
                <Crosshair size={12} /> Identity
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-mono text-cyber-accent uppercase tracking-wider mb-1.5">
                    Workspace Identifier *
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    placeholder="e.g. PRJ-WEBAPP-01"
                    className="w-full bg-cyber-darkest border border-cyber-border focus:border-cyber-accent rounded p-2.5 text-white font-mono text-sm transition-colors focus:outline-none focus:ring-1 focus:ring-cyber-accent placeholder:text-cyber-text/40"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-mono text-cyber-accent uppercase tracking-wider mb-1.5">
                    Scope Description
                  </label>
                  <input
                    type="text"
                    value={description}
                    onChange={e => setDescription(e.target.value)}
                    placeholder="Authorized assessment boundary..."
                    className="w-full bg-cyber-darkest border border-cyber-border focus:border-cyber-accent rounded p-2.5 text-white font-mono text-sm transition-colors focus:outline-none focus:ring-1 focus:ring-cyber-accent placeholder:text-cyber-text/40"
                  />
                </div>
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={!name || creating}
                className="flex items-center gap-2 bg-cyber-accent hover:bg-cyber-accent/80 text-black font-bold uppercase tracking-widest py-2.5 px-6 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm shadow-[0_0_12px_rgba(0,240,255,0.2)] hover:shadow-[0_0_20px_rgba(0,240,255,0.4)]"
              >
                <Plus size={16} />
                {creating ? 'Initializing...' : 'Initialize Workspace'}
              </button>
            </div>

            {error && (
              <div className="bg-red-900/20 border border-red-500/50 text-red-500 p-3 rounded flex items-center gap-2 text-sm font-mono">
                <AlertTriangle size={16} />
                {error}
              </div>
            )}
          </form>

          {/* Animated target beside form */}
          <TargetAcquisition />
        </div>
      </div>

      {/* ── WORKSPACE GRID ── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-mono text-white tracking-widest uppercase text-xs flex items-center gap-2">
            <Activity size={14} className="text-cyber-accent" />
            Security Workspaces
          </h3>
          {!loading && projects.length > 0 && (
            <span className="text-[10px] font-mono text-cyber-text uppercase tracking-widest">
              {projects.length} workspace{projects.length !== 1 ? 's' : ''} found
            </span>
          )}
        </div>

        {loading ? (
          <div className="p-10 text-center text-cyber-accent font-mono animate-pulse border border-cyber-border rounded bg-cyber-darker text-xs uppercase tracking-widest">
            Scanning for workspaces...
          </div>
        ) : projects.length === 0 ? (
          <div className="border border-cyber-border bg-cyber-darker rounded p-16 text-center flex flex-col items-center justify-center gap-4">
            <div className="text-cyber-border">
              <MiniReticle />
            </div>
            <div>
              <h4 className="text-white font-mono uppercase tracking-widest text-sm mb-2">
                No Security Workspaces Detected
              </h4>
              <p className="text-cyber-text text-xs font-mono uppercase tracking-widest max-w-xs mx-auto">
                Initialize an authorized workspace to begin security assessment operations.
              </p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {projects.map((p, idx) => {
              const m = meta[p.id];
              const lastActivity = new Date(p.updated_at).toLocaleDateString('en-GB', {
                day: '2-digit', month: 'short', year: 'numeric'
              });
              return (
                <div
                  key={p.id}
                  onClick={() => onSelectProject(p.id)}
                  className="group bg-cyber-darker border border-cyber-border hover:border-cyber-accent rounded cursor-pointer transition-all duration-200 hover:shadow-[0_0_20px_rgba(0,240,255,0.12)] hover:-translate-y-0.5 relative overflow-hidden flex flex-col animate-fade-in-up"
                  style={{ animationDelay: `${idx * 0.05}s` }}
                  role="button"
                  tabIndex={0}
                  aria-label={`Open workspace ${p.name}`}
                  onKeyDown={e => e.key === 'Enter' && onSelectProject(p.id)}
                >
                  {/* Left accent bar */}
                  <div className="absolute top-0 left-0 w-[3px] h-full bg-cyber-border group-hover:bg-cyber-accent transition-colors duration-200"></div>

                  {/* Card Header */}
                  <div className="flex items-start justify-between px-5 pt-4 pb-3 ml-1 border-b border-cyber-border/50">
                    <div className="flex-1 min-w-0 pr-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[9px] font-mono text-cyber-text/60 uppercase tracking-widest">
                          WS-{String(p.id).padStart(4, '0')}
                        </span>
                        {m && <StatusBadge status={m.status} />}
                      </div>
                      <h4 className="text-white font-bold font-mono tracking-wide text-base truncate">
                        {p.name}
                      </h4>
                    </div>
                    <div className="text-cyber-accent/50 group-hover:text-cyber-accent transition-colors flex-shrink-0 mt-0.5">
                      <MiniReticle active={m?.status === 'ACTIVE'} />
                    </div>
                  </div>

                  {/* Scope */}
                  <div className="px-5 py-3 ml-1">
                    <p className="text-[10px] font-mono text-cyber-text/60 uppercase tracking-widest mb-0.5">Scope</p>
                    <p className="text-xs text-cyber-text line-clamp-2 font-mono">
                      {p.description || 'No scope defined'}
                    </p>
                  </div>

                  {/* Stats Row */}
                  <div className="px-5 py-3 ml-1 border-t border-cyber-border/50 grid grid-cols-2 gap-3">
                    <div>
                      <p className="text-[10px] font-mono text-cyber-text/60 uppercase tracking-widest mb-0.5">Assessments</p>
                      <p className="text-sm font-mono font-bold text-white">
                        {m !== undefined ? String(m.assessmentCount).padStart(2, '0') : '--'}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] font-mono text-cyber-text/60 uppercase tracking-widest mb-0.5">Last Activity</p>
                      <p className="text-xs font-mono text-cyber-text">{lastActivity}</p>
                    </div>
                  </div>

                  {/* Footer CTA */}
                  <div className="px-5 py-3 ml-1 border-t border-cyber-border/50 flex items-center justify-between">
                    <span className="text-[10px] font-mono text-cyber-text/50 uppercase tracking-widest">
                      {m?.hasActive ? 'Operation in progress' : 'Ready for assessment'}
                    </span>
                    <span className="flex items-center gap-1 text-[10px] font-mono text-cyber-accent opacity-0 group-hover:opacity-100 transition-opacity duration-200 uppercase tracking-widest font-bold">
                      Enter Console <ArrowRight size={12} />
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
