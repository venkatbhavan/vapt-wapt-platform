import { useState, useEffect, useMemo } from 'react';
import { ArrowLeft, Search, ChevronDown, ChevronRight, Wrench, AlertTriangle, ShieldCheck } from 'lucide-react';
import { AssessmentRemediationResponse } from '../types/remediation';

interface RemediationViewProps {
  assessmentId: number;
  onBack: () => void;
  onViewFinding: (findingId: number) => void;
}

const getPriorityColor = (priority: string) => {
  switch (priority?.toLowerCase()) {
    case 'critical': return 'text-purple-500 bg-purple-500/10 border-purple-500/20';
    case 'high': return 'text-red-500 bg-red-500/10 border-red-500/20';
    case 'medium': return 'text-orange-500 bg-orange-500/10 border-orange-500/20';
    case 'low': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
    default: return 'text-cyber-accent bg-cyber-accent/10 border-cyber-accent/20';
  }
};

const getSeverityColor = (severity: string) => {
  switch (severity?.toLowerCase()) {
    case 'critical': return 'text-purple-500 bg-purple-500/10 border-purple-500/20';
    case 'high': return 'text-red-500 bg-red-500/10 border-red-500/20';
    case 'medium': return 'text-orange-500 bg-orange-500/10 border-orange-500/20';
    case 'low': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
    default: return 'text-cyber-accent bg-cyber-accent/10 border-cyber-accent/20';
  }
};

const Badge = ({ text, colorClass }: { text: string; colorClass: string }) => (
  <span className={`px-2 py-0.5 rounded text-xs border font-medium uppercase ${colorClass}`}>
    {text}
  </span>
);

export function RemediationView({ assessmentId, onBack, onViewFinding }: RemediationViewProps) {
  const [data, setData] = useState<AssessmentRemediationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Filters
  const [filterPriority, setFilterPriority] = useState<string>('all');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterType, setFilterType] = useState<string>('all');

  const [expandedCards, setExpandedCards] = useState<Set<number>>(new Set());

  useEffect(() => {
    fetchData();
  }, [assessmentId]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`http://localhost:8000/api/assessments/${assessmentId}/remediation`);
      if (!response.ok) {
        throw new Error('Unable to load remediation data.');
      }
      const result: AssessmentRemediationResponse = await response.json();
      setData(result);
    } catch (err: any) {
      setError(err.message || 'API Error');
    } finally {
      setLoading(false);
    }
  };

  const toggleCard = (id: number) => {
    const next = new Set(expandedCards);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setExpandedCards(next);
  };

  const resetFilters = () => {
    setSearchQuery('');
    setFilterPriority('all');
    setFilterSeverity('all');
    setFilterType('all');
  };

  // Extract filter options dynamically from data
  const availablePriorities = useMemo(() => {
    if (!data) return [];
    return Array.from(new Set(data.remediations.map(r => r.priority))).sort();
  }, [data]);

  const availableSeverities = useMemo(() => {
    if (!data) return [];
    const severities = new Set<string>();
    data.remediations.forEach(r => r.mappings.forEach(m => severities.add(m.finding.severity)));
    return Array.from(severities).sort();
  }, [data]);

  const availableTypes = useMemo(() => {
    if (!data) return [];
    return Array.from(new Set(data.remediations.map(r => r.remediation_type))).sort();
  }, [data]);

  // Derived filtered data
  const filteredRemediations = useMemo(() => {
    if (!data) return [];
    
    let result = data.remediations;
    const query = searchQuery.toLowerCase();

    // Text Search
    if (query) {
      result = result.filter(r => {
        const matchGuidance = 
          r.title.toLowerCase().includes(query) ||
          r.summary.toLowerCase().includes(query) ||
          r.detailed_guidance.toLowerCase().includes(query) ||
          r.verification_guidance.toLowerCase().includes(query) ||
          r.remediation_type.toLowerCase().includes(query);

        const matchMappings = r.mappings.some(m => 
          m.finding.title.toLowerCase().includes(query) ||
          (m.finding.normalized_type && m.finding.normalized_type.toLowerCase().includes(query))
        );

        return matchGuidance || matchMappings;
      });
    }

    // Filters
    if (filterPriority !== 'all') {
      result = result.filter(r => r.priority === filterPriority);
    }

    if (filterType !== 'all') {
      result = result.filter(r => r.remediation_type === filterType);
    }

    if (filterSeverity !== 'all') {
      result = result.filter(r => r.mappings.some(m => m.finding.severity === filterSeverity));
    }

    return result;
  }, [data, searchQuery, filterPriority, filterSeverity, filterType]);

  // Summary Metrics
  const metrics = useMemo(() => {
    if (!data) return { guidance: 0, findings: 0, criticalFindings: 0, highPriority: 0 };
    
    const uniqueFindings = new Set<number>();
    let criticalFindingsCount = 0;
    
    data.remediations.forEach(r => {
      r.mappings.forEach(m => {
        if (!uniqueFindings.has(m.finding.id)) {
          uniqueFindings.add(m.finding.id);
          if (m.finding.severity === 'critical') {
            criticalFindingsCount++;
          }
        }
      });
    });

    return {
      guidance: data.remediations.length,
      findings: uniqueFindings.size,
      criticalFindings: criticalFindingsCount,
      highPriority: data.remediations.filter(r => r.priority === 'high' || r.priority === 'critical').length
    };
  }, [data]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyber-accent"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 p-6 rounded-lg text-center">
        <AlertTriangle className="mx-auto text-red-500 mb-2" size={32} />
        <h3 className="text-lg font-medium text-red-500 mb-4">Unable to load remediation data.</h3>
        <button
          onClick={fetchData}
          className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  if (data && data.remediations.length === 0) {
    return (
      <div>
        <div className="mb-6 flex items-center gap-4">
          <button onClick={onBack} className="p-2 hover:bg-cyber-dark rounded-full transition-colors text-cyber-text">
            <ArrowLeft size={20} />
          </button>
          <div>
            <h2 className="text-2xl font-bold text-white">Remediation</h2>
            <p className="text-sm text-cyber-text">Actionable remediation guidance derived from the assessment findings.</p>
          </div>
        </div>
        <div className="bg-cyber-darker border border-cyber-border p-8 rounded-lg text-center">
          <ShieldCheck className="mx-auto text-cyber-border mb-4" size={48} />
          <h3 className="text-xl font-medium text-white mb-2">No remediation guidance available</h3>
          <p className="text-cyber-text">Remediation guidance will appear when findings have applicable remediation mappings.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button onClick={onBack} className="p-2 hover:bg-cyber-dark rounded-full transition-colors text-cyber-text">
          <ArrowLeft size={20} />
        </button>
        <div>
          <h2 className="text-2xl font-bold text-white">Remediation</h2>
          <p className="text-sm text-cyber-text">Actionable remediation guidance derived from the assessment findings.</p>
        </div>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-cyber-darker border border-cyber-border p-4 rounded-lg">
          <p className="text-xs text-cyber-text mb-1">Remediation Guidance</p>
          <p className="text-2xl font-semibold text-white">{metrics.guidance}</p>
        </div>
        <div className="bg-cyber-darker border border-cyber-border p-4 rounded-lg">
          <p className="text-xs text-cyber-text mb-1">Affected Findings</p>
          <p className="text-2xl font-semibold text-white">{metrics.findings}</p>
        </div>
        <div className="bg-cyber-darker border border-cyber-border p-4 rounded-lg">
          <p className="text-xs text-cyber-text mb-1">Critical Findings</p>
          <p className="text-2xl font-semibold text-red-500">{metrics.criticalFindings}</p>
        </div>
        <div className="bg-cyber-darker border border-cyber-border p-4 rounded-lg">
          <p className="text-xs text-cyber-text mb-1">High Priority</p>
          <p className="text-2xl font-semibold text-white">{metrics.highPriority}</p>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="bg-cyber-darker border border-cyber-border p-4 rounded-lg space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 text-cyber-text" size={18} />
          <input
            type="text"
            placeholder="Search remediation guidance or findings..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-cyber-darkest border border-cyber-border rounded pl-10 pr-4 py-2 text-white focus:outline-none focus:border-cyber-accent"
          />
        </div>
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-cyber-text">Priority:</span>
            <select
              value={filterPriority}
              onChange={(e) => setFilterPriority(e.target.value)}
              className="bg-cyber-darkest border border-cyber-border rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-cyber-accent"
            >
              <option value="all">All Priorities</option>
              {availablePriorities.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-sm text-cyber-text">Severity:</span>
            <select
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              className="bg-cyber-darkest border border-cyber-border rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-cyber-accent"
            >
              <option value="all">All Severities</option>
              {availableSeverities.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm text-cyber-text">Type:</span>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="bg-cyber-darkest border border-cyber-border rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-cyber-accent"
            >
              <option value="all">All Types</option>
              {availableTypes.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          
          {(searchQuery || filterPriority !== 'all' || filterSeverity !== 'all' || filterType !== 'all') && (
            <button
              onClick={resetFilters}
              className="text-sm text-cyber-accent hover:text-cyber-accent ml-auto"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Filtered Empty State */}
      {filteredRemediations.length === 0 && (
        <div className="bg-cyber-darker border border-cyber-border p-8 rounded-lg text-center">
          <p className="text-cyber-text mb-4">No remediation items match your current filters.</p>
          <button
            onClick={resetFilters}
            className="text-cyber-accent hover:text-cyber-accent"
          >
            Reset search and filters
          </button>
        </div>
      )}

      {/* Remediation Cards */}
      <div className="space-y-4">
        {filteredRemediations.map((rem) => {
          const isExpanded = expandedCards.has(rem.id);

          return (
            <div key={rem.id} className="bg-cyber-darker border border-cyber-border rounded-lg overflow-hidden">
              <button
                onClick={() => toggleCard(rem.id)}
                className="w-full text-left p-4 hover:bg-cyber-dark/50 transition-colors flex items-start gap-4"
              >
                <div className="mt-1 text-cyber-text">
                  {isExpanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                </div>
                <div className="flex-1">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 mb-2">
                    <h3 className="text-lg font-semibold text-white">{rem.title}</h3>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-cyber-text">Priority:</span>
                      <Badge text={rem.priority} colorClass={getPriorityColor(rem.priority)} />
                      <span className="text-xs text-cyber-text ml-2">Type:</span>
                      <span className="px-2 py-0.5 rounded text-xs border font-medium uppercase text-cyber-accent bg-cyber-accent/10 border-cyber-accent/20">
                        {rem.remediation_type}
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-cyber-textBright mb-2">{rem.summary}</p>
                  <div className="text-xs text-cyber-text flex items-center gap-1">
                    <Wrench size={14} /> Affected findings: {rem.mappings.length}
                  </div>
                </div>
              </button>

              {isExpanded && (
                <div className="p-4 border-t border-cyber-border bg-cyber-darkest/50 space-y-6">
                  {/* Guidance Detail */}
                  <div className="space-y-4">
                    <div>
                      <h4 className="text-sm font-semibold text-cyber-text mb-1 uppercase tracking-wider">Detailed Guidance</h4>
                      <p className="text-sm text-cyber-textBright whitespace-pre-wrap">{rem.detailed_guidance}</p>
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-cyber-text mb-1 uppercase tracking-wider">Verification Guidance</h4>
                      <p className="text-sm text-cyber-textBright whitespace-pre-wrap">{rem.verification_guidance}</p>
                    </div>
                  </div>

                  {/* Affected Findings */}
                  <div>
                    <h4 className="text-sm font-semibold text-cyber-text mb-3 uppercase tracking-wider">Affected Findings ({rem.mappings.length})</h4>
                    <div className="space-y-2">
                      {rem.mappings.map((mapping) => (
                        <div key={mapping.id} className="bg-cyber-darker border border-cyber-border rounded p-3 flex flex-col md:flex-row justify-between md:items-center gap-4 hover:border-cyber-border transition-colors">
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <Badge text={mapping.finding.severity} colorClass={getSeverityColor(mapping.finding.severity)} />
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onViewFinding(mapping.finding.id);
                                }}
                                className="text-cyber-accent hover:text-cyber-accent hover:underline font-medium text-sm text-left"
                              >
                                {mapping.finding.title}
                              </button>
                            </div>
                            <div className="flex flex-wrap gap-3 text-xs text-cyber-text mt-2">
                              {mapping.finding.normalized_type && (
                                <span>Type: <span className="text-cyber-text">{mapping.finding.normalized_type}</span></span>
                              )}
                              <span>Status: <span className="text-cyber-text">{mapping.finding.status}</span></span>
                              <span>Mapping Confidence: <span className="text-cyber-text">{mapping.mapping_confidence}</span></span>
                            </div>
                            <div className="text-xs text-cyber-text mt-2 border-l-2 border-cyber-border pl-2">
                              {mapping.rationale}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
