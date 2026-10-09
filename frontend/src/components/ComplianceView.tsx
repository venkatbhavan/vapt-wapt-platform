import { useState, useEffect, useMemo } from 'react';
import { ArrowLeft, Activity, Search, ChevronDown, ChevronRight, Book, ShieldAlert, AlertTriangle } from 'lucide-react';
import { ComplianceAssessment } from '../types/compliance';

interface ComplianceViewProps {
  assessmentId: number;
  onBack: () => void;
  onViewFinding: (findingId: number) => void;
}

const getSeverityColor = (severity: string) => {
  switch (severity?.toLowerCase()) {
    case 'critical': return 'text-purple-500 bg-purple-500/10 border-purple-500/20';
    case 'high': return 'text-red-500 bg-red-500/10 border-red-500/20';
    case 'medium': return 'text-orange-500 bg-orange-500/10 border-orange-500/20';
    case 'low': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
    default: return 'text-cyber-accent bg-cyber-accent/10 border-cyber-accent/20';
  }
};

const getSeverityBadge = (severity: string) => (
  <span className={`px-2 py-0.5 rounded text-xs border font-mono uppercase ${getSeverityColor(severity)}`}>
    {severity}
  </span>
);

export function ComplianceView({ assessmentId, onBack, onViewFinding }: ComplianceViewProps) {
  const [data, setData] = useState<ComplianceAssessment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Filters
  const [filterType, setFilterType] = useState<string>('all');
  const [filterConfidence, setFilterConfidence] = useState<string>('all');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');

  // Expanded state (framework IDs and control IDs)
  const [expandedFrameworks, setExpandedFrameworks] = useState<Set<number>>(new Set());
  const [expandedControls, setExpandedControls] = useState<Set<number>>(new Set());

  useEffect(() => {
    fetchData();
  }, [assessmentId]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}`}/api/assessments/${assessmentId}/compliance`);
      if (!response.ok) {
        throw new Error('Unable to load compliance data.');
      }
      const result: ComplianceAssessment = await response.json();
      setData(result);

      // Auto-expand the first framework by default
      if (result.frameworks.length > 0) {
        setExpandedFrameworks(new Set([result.frameworks[0].id]));
      }
    } catch (err: any) {
      setError(err.message || 'API Error');
    } finally {
      setLoading(false);
    }
  };

  const toggleFramework = (id: number) => {
    const next = new Set(expandedFrameworks);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setExpandedFrameworks(next);
  };

  const toggleControl = (id: number) => {
    const next = new Set(expandedControls);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setExpandedControls(next);
  };

  // Filter & Search Logic
  const filteredFrameworks = useMemo(() => {
    if (!data) return [];

    return data.frameworks.map(fw => {
      const controls = fw.controls.map(ctrl => {
        const mappings = ctrl.mappings.filter(m => {
          // Status/Type/Severity filters
          if (filterType !== 'all' && m.mapping_type !== filterType) return false;
          if (filterConfidence !== 'all' && m.mapping_confidence !== filterConfidence) return false;
          if (filterSeverity !== 'all' && m.finding_severity?.toLowerCase() !== filterSeverity) return false;

          // Search filter
          if (searchQuery) {
            const sq = searchQuery.toLowerCase();
            return (
              fw.name.toLowerCase().includes(sq) ||
              ctrl.control_id.toLowerCase().includes(sq) ||
              ctrl.title.toLowerCase().includes(sq) ||
              m.finding_title.toLowerCase().includes(sq)
            );
          }

          return true;
        });

        return { ...ctrl, mappings };
      }).filter(ctrl => {
        // Only keep control if it has mappings after filtering, OR if search query matches the control/framework
        const sq = searchQuery.toLowerCase();
        const matchesSearch = sq && (fw.name.toLowerCase().includes(sq) || ctrl.control_id.toLowerCase().includes(sq) || ctrl.title.toLowerCase().includes(sq));
        return ctrl.mappings.length > 0 || (searchQuery && matchesSearch);
      });

      return { ...fw, controls };
    }).filter(fw => fw.controls.length > 0);
  }, [data, searchQuery, filterType, filterConfidence, filterSeverity]);

  // Calculate summary metrics
  const summary = useMemo(() => {
    if (!data) return { frameworks: 0, controls: 0, mappings: 0, uniqueFindings: 0 };

    let ctrlCount = 0;
    let mappingCount = 0;
    const uniqueFindings = new Set<number>();

    // We calculate this from the API response (filtered or unfiltered? usually summary counts all unfiltered but filtered is also fine. Requirement says calculate from API response. Let's do raw total mappings).
    data.frameworks.forEach(fw => {
      fw.controls.forEach(c => {
        if (c.mappings.length > 0) {
          ctrlCount++;
          c.mappings.forEach(m => {
            mappingCount++;
            uniqueFindings.add(m.finding_id);
          });
        }
      });
    });

    return {
      frameworks: data.frameworks.filter(fw => fw.controls.some(c => c.mappings.length > 0)).length,
      controls: ctrlCount,
      mappings: mappingCount,
      uniqueFindings: uniqueFindings.size
    };
  }, [data]);

  if (loading) {
    return <div className="text-cyber-text p-8 flex gap-3 items-center font-mono uppercase tracking-widest"><Activity className="animate-spin text-cyber-accent" size={20} /> Loading compliance...</div>;
  }

  if (error) {
    return (
      <div className="space-y-6">
        <button onClick={onBack} className="border border-cyber-accent text-cyber-accent hover:bg-cyber-accent hover:text-black font-bold uppercase tracking-widest py-2 px-4 rounded transition-colors font-mono text-sm flex items-center gap-2">
          <ArrowLeft size={16} /> BACK
        </button>
        <div className="bg-red-500/10 border border-red-500 p-4 rounded flex flex-col items-start gap-4">
          <div className="flex items-center gap-3 text-red-500">
            <AlertTriangle size={20} />
            <p className="font-mono uppercase text-sm tracking-widest">{error}</p>
          </div>
          <button onClick={fetchData} className="border border-red-500 text-red-500 hover:bg-red-500 hover:text-black font-bold uppercase tracking-widest py-2 px-4 rounded transition-colors font-mono text-sm">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (data && data.frameworks.length === 0) {
    return (
      <div className="space-y-6">
        <button onClick={onBack} className="border border-cyber-accent text-cyber-accent hover:bg-cyber-accent hover:text-black font-bold uppercase tracking-widest py-2 px-4 rounded transition-colors font-mono text-sm flex items-center gap-2">
          <ArrowLeft size={16} /> BACK
        </button>
        <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-8 text-center flex flex-col items-center justify-center">
          <ShieldAlert size={48} className="text-cyber-border mb-4" />
          <h3 className="text-white font-mono uppercase tracking-widest mb-2">No compliance mappings found</h3>
          <p className="text-cyber-text">Compliance mappings will appear here when findings are mapped to supported compliance controls.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <button onClick={onBack} className="border border-cyber-accent text-cyber-accent hover:bg-cyber-accent hover:text-black font-bold uppercase tracking-widest py-2 px-4 rounded transition-colors font-mono text-sm flex items-center gap-2 mb-4">
            <ArrowLeft size={16} /> BACK
          </button>
          <div className="bg-cyber-darkest border border-cyber-border p-4 flex items-center gap-3 rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] mb-2">
            <Book size={18} className="text-cyber-accent" />
            <h3 className="font-mono text-white tracking-widest uppercase text-sm">Compliance</h3>
          </div>
          <p className="text-cyber-text mt-1 text-sm font-mono uppercase tracking-wider">Framework and control coverage for this assessment</p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
          <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
            <Activity size={18} className="text-cyber-accent" />
            <h3 className="font-mono text-white tracking-widest uppercase text-sm">Frameworks</h3>
          </div>
          <div className="p-4">
            <p className="text-2xl font-bold text-white">{summary.frameworks}</p>
          </div>
        </div>
        <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
          <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
            <ShieldAlert size={18} className="text-cyber-accent" />
            <h3 className="font-mono text-white tracking-widest uppercase text-sm">Controls</h3>
          </div>
          <div className="p-4">
            <p className="text-2xl font-bold text-white">{summary.controls}</p>
          </div>
        </div>
        <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
          <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
            <Search size={18} className="text-cyber-accent" />
            <h3 className="font-mono text-white tracking-widest uppercase text-sm">Mapped Findings</h3>
          </div>
          <div className="p-4">
            <p className="text-2xl font-bold text-white">{summary.uniqueFindings}</p>
          </div>
        </div>
        <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
          <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
            <Book size={18} className="text-cyber-accent" />
            <h3 className="font-mono text-white tracking-widest uppercase text-sm">Mappings</h3>
          </div>
          <div className="p-4">
            <p className="text-2xl font-bold text-white">{summary.mappings}</p>
          </div>
        </div>
      </div>

      <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-4 flex flex-col md:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-2.5 text-cyber-text" size={18} />
          <input
            type="text"
            placeholder="SEARCH..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-cyber-darkest border border-cyber-border rounded pl-10 pr-4 py-2 text-white focus:outline-none focus:border-cyber-accent transition-colors font-mono text-sm uppercase tracking-wider"
          />
        </div>

        <div className="flex gap-2">
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="bg-cyber-darkest border border-cyber-border rounded px-3 py-2 text-white focus:outline-none focus:border-cyber-accent font-mono text-sm uppercase tracking-wider"
          >
            <option value="all">All Types</option>
            <option value="direct">Direct</option>
            <option value="related">Related</option>
          </select>
          <select
            value={filterConfidence}
            onChange={(e) => setFilterConfidence(e.target.value)}
            className="bg-cyber-darkest border border-cyber-border rounded px-3 py-2 text-white focus:outline-none focus:border-cyber-accent font-mono text-sm uppercase tracking-wider"
          >
            <option value="all">All Confidence</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="bg-cyber-darkest border border-cyber-border rounded px-3 py-2 text-white focus:outline-none focus:border-cyber-accent font-mono text-sm uppercase tracking-wider"
          >
            <option value="all">All Severity</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="info">Info</option>
          </select>
        </div>
      </div>

      <div className="space-y-4">
        {filteredFrameworks.length === 0 ? (
          <div className="text-center p-8 text-cyber-text border border-cyber-border border-dashed rounded">
            No compliance mappings match your search criteria.
          </div>
        ) : (
          filteredFrameworks.map(fw => (
            <div key={fw.id} className="border border-cyber-border rounded overflow-hidden bg-cyber-darker">
              <button
                onClick={() => toggleFramework(fw.id)}
                className="w-full flex items-center justify-between p-4 bg-cyber-dark/50 hover:bg-cyber-dark transition-colors"
              >
                <div className="flex flex-col items-start text-left">
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-white">{fw.name} {fw.version}</span>
                  </div>
                  {fw.description && <p className="text-sm text-cyber-text mt-1">{fw.description}</p>}
                </div>
                <div className="flex items-center gap-6">
                  <div className="flex gap-4 text-sm text-cyber-text text-right">
                    <span>Controls: <strong className="text-white">{fw.controls.length}</strong></span>
                    <span>Mapped Findings: <strong className="text-white">{fw.controls.reduce((acc, c) => acc + c.mappings.length, 0)}</strong></span>
                  </div>
                  {expandedFrameworks.has(fw.id) ? <ChevronDown size={20} className="text-cyber-text" /> : <ChevronRight size={20} className="text-cyber-text" />}
                </div>
              </button>

              {expandedFrameworks.has(fw.id) && (
                <div className="p-4 space-y-3">
                  {fw.controls.map(ctrl => (
                    <div key={ctrl.id} className="border border-cyber-border/50 rounded bg-cyber-darkest overflow-hidden">
                      <button
                        onClick={() => toggleControl(ctrl.id)}
                        className="w-full flex items-center justify-between p-3 hover:bg-cyber-darker transition-colors text-left"
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-cyber-accent text-sm">{ctrl.control_id}</span>
                            <span className="font-medium text-cyber-textBright">{ctrl.title}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-4 text-sm">
                          <span className="text-cyber-text">Mappings: <strong className="text-cyber-textBright">{ctrl.mappings.length}</strong></span>
                          {expandedControls.has(ctrl.id) ? <ChevronDown size={16} className="text-cyber-text" /> : <ChevronRight size={16} className="text-cyber-text" />}
                        </div>
                      </button>

                      {expandedControls.has(ctrl.id) && (
                        <div className="p-3 border-t border-cyber-border bg-cyber-darker/50 space-y-3">
                          {ctrl.description && <p className="text-sm text-cyber-text mb-3 px-1">{ctrl.description}</p>}

                          <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                            {ctrl.mappings.map(mapping => (
                              <div key={mapping.id} className="bg-cyber-darkest border border-cyber-border p-3 rounded shadow-sm flex flex-col gap-2">
                                <div className="flex justify-between items-start">
                                  <button
                                    onClick={() => onViewFinding(mapping.finding_id)}
                                    className="text-white font-medium hover:text-cyber-accent transition-colors text-left"
                                  >
                                    {mapping.finding_title}
                                  </button>
                                  {getSeverityBadge(mapping.finding_severity)}
                                </div>
                                <div className="flex items-center gap-3 text-xs text-cyber-text font-mono">
                                  <span>Finding #{mapping.finding_id}</span>
                                  <span>•</span>
                                  <span className="uppercase">Status: {mapping.finding_status}</span>
                                </div>

                                <div className="mt-1 pt-2 border-t border-cyber-border/50 grid grid-cols-2 gap-2 text-xs">
                                  <div>
                                    <span className="text-cyber-text block">Mapping</span>
                                    <span className="text-cyber-textBright capitalize">{mapping.mapping_type}</span>
                                  </div>
                                  <div>
                                    <span className="text-cyber-text block">Confidence</span>
                                    <span className="text-cyber-textBright capitalize">{mapping.mapping_confidence}</span>
                                  </div>
                                  {mapping.rationale && (
                                    <div className="col-span-2 mt-1">
                                      <span className="text-cyber-text block">Rationale</span>
                                      <span className="text-cyber-text">{mapping.rationale}</span>
                                    </div>
                                  )}
                                  <div className="col-span-2 mt-1">
                                    <span className="text-cyber-text block">Source</span>
                                    <span className="text-cyber-text">{mapping.source}</span>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
