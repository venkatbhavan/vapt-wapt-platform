import { useState, useEffect } from 'react';
import { ArrowLeft, Server, Globe, Box, ShieldAlert, Activity, Search, AlertCircle, ChevronDown, ChevronRight } from 'lucide-react';
import {
    AttackSurfaceResponse,
    AttackSurfaceFinding
} from '../types/attackSurface';

interface AttackSurfaceViewProps {
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
  <span className={`px-2 py-0.5 rounded text-xs border font-medium uppercase ${getSeverityColor(severity)}`}>
    {severity}
  </span>
);

export function AttackSurfaceView({ assessmentId, onBack, onViewFinding }: AttackSurfaceViewProps) {
  const [data, setData] = useState<AttackSurfaceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedAssets, setExpandedAssets] = useState<Set<number>>(new Set());

  useEffect(() => {
    fetchData();
  }, [assessmentId]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`http://localhost:8000/api/assessments/${assessmentId}/attack-surface`);
      if (!response.ok) {
        throw new Error('Failed to fetch attack surface');
      }
      const result: AttackSurfaceResponse = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  const toggleAsset = (assetId: number) => {
    const next = new Set(expandedAssets);
    if (next.has(assetId)) {
      next.delete(assetId);
    } else {
      next.add(assetId);
    }
    setExpandedAssets(next);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64 text-cyber-text gap-3">
        <Activity className="animate-spin" size={24} /> Loading attack surface...
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <button onClick={onBack} className="flex items-center gap-2 text-cyber-text hover:text-white transition-colors">
          <ArrowLeft size={16} /> Back to Dashboard
        </button>
        <div className="bg-red-500/10 border border-red-500 text-red-500 p-6 rounded-lg flex items-center gap-4">
          <AlertCircle size={24} />
          <div>
            <h3 className="font-bold">Unable to load attack surface</h3>
            <p className="text-sm mt-1">{error}</p>
            <button onClick={fetchData} className="mt-3 text-sm underline hover:text-red-400">Try again</button>
          </div>
        </div>
      </div>
    );
  }

  if (!data || data.assets.length === 0) {
    return (
      <div className="space-y-6">
        <button onClick={onBack} className="flex items-center gap-2 text-cyber-text hover:text-white transition-colors">
          <ArrowLeft size={16} /> Back to Dashboard
        </button>
        <div className="bg-cyber-darker border border-cyber-border rounded-lg p-12 text-center">
          <Server size={48} className="mx-auto text-cyber-border mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">No attack surface discovered yet</h2>
          <p className="text-cyber-text">Run an authorized Nmap or ZAP assessment to populate the attack surface.</p>
        </div>
      </div>
    );
  }

  // Calculate Metrics
  let totalAssets = data.assets.length;
  let totalServices = 0;
  let totalWebApps = 0;
  let totalEndpoints = 0;
  let totalFindings = 0;
  const severityCounts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };

  const countFinding = (f: AttackSurfaceFinding) => {
    totalFindings++;
    const sev = f.severity?.toLowerCase() as keyof typeof severityCounts;
    if (severityCounts[sev] !== undefined) {
      severityCounts[sev]++;
    }
  };

  data.assets.forEach(a => {
    a.findings.forEach(countFinding);
    a.services.forEach(s => {
      totalServices++;
      s.findings.forEach(countFinding);
    });
    a.web_applications.forEach(w => {
      totalWebApps++;
      w.findings.forEach(countFinding);
      w.endpoints.forEach(e => {
        totalEndpoints++;
        e.findings.forEach(countFinding);
      });
    });
  });

  // Simple Filtering (search IP or hostname)
  const filteredAssets = data.assets.filter(a =>
    a.ip_address.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (a.hostname && a.hostname.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const renderFinding = (f: AttackSurfaceFinding) => (
    <div key={f.id} className="ml-4 mt-2 mb-2 p-3 bg-cyber-dark border border-cyber-border rounded text-sm hover:border-cyber-text/70 cursor-pointer" onClick={() => onViewFinding(f.id)}>
      <div className="flex items-center justify-between mb-1">
        <span className="font-semibold text-cyber-textBright">{f.title}</span>
        {getSeverityBadge(f.severity)}
      </div>
      <div className="text-cyber-text text-xs flex gap-4">
        <span>Risk: {f.risk_level || '-'}</span>
        <span>Status: <span className="uppercase text-cyber-textBright">{f.status}</span></span>
        {f.location && <span className="truncate">Loc: {f.location}</span>}
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <button onClick={onBack} className="flex items-center gap-2 text-cyber-text hover:text-white transition-colors">
          <ArrowLeft size={16} /> Back to Dashboard
        </button>
      </div>

      {/* Metrics Overview */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-cyber-darker border border-cyber-border p-4 rounded-lg flex items-center justify-between">
          <div><p className="text-xs text-cyber-text uppercase">Assets</p><p className="text-2xl font-bold text-white">{totalAssets}</p></div>
          <Server className="text-cyber-accent opacity-50" size={24}/>
        </div>
        <div className="bg-cyber-darker border border-cyber-border p-4 rounded-lg flex items-center justify-between">
          <div><p className="text-xs text-cyber-text uppercase">Services</p><p className="text-2xl font-bold text-white">{totalServices}</p></div>
          <Activity className="text-green-500 opacity-50" size={24}/>
        </div>
        <div className="bg-cyber-darker border border-cyber-border p-4 rounded-lg flex items-center justify-between">
          <div><p className="text-xs text-cyber-text uppercase">Web Apps</p><p className="text-2xl font-bold text-white">{totalWebApps}</p></div>
          <Globe className="text-purple-500 opacity-50" size={24}/>
        </div>
        <div className="bg-cyber-darker border border-cyber-border p-4 rounded-lg flex items-center justify-between">
          <div><p className="text-xs text-cyber-text uppercase">Endpoints</p><p className="text-2xl font-bold text-white">{totalEndpoints}</p></div>
          <Box className="text-orange-500 opacity-50" size={24}/>
        </div>
        <div className="bg-cyber-darker border border-cyber-border p-4 rounded-lg flex items-center justify-between">
          <div><p className="text-xs text-cyber-text uppercase">Findings</p><p className="text-2xl font-bold text-white">{totalFindings}</p></div>
          <ShieldAlert className="text-red-500 opacity-50" size={24}/>
        </div>
      </div>

      {/* Risk Summary */}
      <div className="bg-cyber-darker border border-cyber-border rounded-lg p-4 flex flex-wrap gap-6 items-center">
        <span className="text-sm font-semibold text-cyber-text uppercase tracking-wider">Risk Summary</span>
        <div className="flex gap-4 text-sm">
          <span className="text-purple-400">Critical: {severityCounts.critical}</span>
          <span className="text-red-400">High: {severityCounts.high}</span>
          <span className="text-orange-400">Medium: {severityCounts.medium}</span>
          <span className="text-yellow-400">Low: {severityCounts.low}</span>
          <span className="text-cyber-accent">Info: {severityCounts.info}</span>
        </div>
      </div>

      {/* Search & Filter */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-cyber-text" size={16} />
          <input
            type="text"
            placeholder="Search by IP or hostname..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full bg-cyber-darker border border-cyber-border text-white rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:border-cyber-accent"
          />
        </div>
      </div>

      {/* Asset Inventory */}
      <div className="space-y-4">
        {filteredAssets.map(asset => (
          <div key={asset.id} className="bg-cyber-darker border border-cyber-border rounded-lg overflow-hidden">

            {/* Asset Header */}
            <div
              className="p-4 flex items-center justify-between cursor-pointer hover:bg-cyber-dark transition-colors"
              onClick={() => toggleAsset(asset.id)}
            >
              <div className="flex items-center gap-4">
                {expandedAssets.has(asset.id) ? <ChevronDown size={20} className="text-cyber-text" /> : <ChevronRight size={20} className="text-cyber-text" />}
                <div>
                  <h3 className="text-lg font-bold text-white flex items-center gap-2">
                    {asset.ip_address}
                    {asset.hostname && <span className="text-cyber-text font-normal text-sm">({asset.hostname})</span>}
                  </h3>
                  <div className="text-xs text-cyber-text flex gap-4 mt-1">
                    {asset.os && <span>OS: {asset.os}</span>}
                    <span className="uppercase">{asset.status}</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-4 text-sm text-cyber-text">
                <span>Services: <strong className="text-white">{asset.services.length}</strong></span>
                <span>Web Apps: <strong className="text-white">{asset.web_applications.length}</strong></span>
                <span>Findings: <strong className="text-red-400">{asset.findings.length}</strong></span>
              </div>
            </div>

            {/* Asset Body (Expanded) */}
            {expandedAssets.has(asset.id) && (
              <div className="p-4 border-t border-cyber-border bg-cyber-darkest space-y-6">

                {/* Asset Findings */}
                {asset.findings.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-cyber-text uppercase mb-2">Asset Findings</h4>
                    {asset.findings.map(renderFinding)}
                  </div>
                )}

                {/* Services */}
                {asset.services.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-cyber-text uppercase mb-2">Network Services</h4>
                    <div className="space-y-3 pl-4 border-l-2 border-cyber-border ml-2">
                      {asset.services.map(svc => (
                        <div key={svc.id} className="p-3 bg-cyber-darker border border-cyber-border rounded-lg">
                          <div className="flex justify-between items-center mb-2">
                            <div className="flex gap-3 items-center">
                              <span className="text-white font-mono font-bold">{svc.protocol.toUpperCase()} {svc.port}</span>
                              <span className="px-2 py-0.5 bg-cyber-dark text-cyber-textBright text-xs rounded">{svc.state}</span>
                              {svc.service_name && <span className="text-cyber-text text-sm">{svc.service_name}</span>}
                            </div>
                            <span className="text-xs text-red-400">Findings: {svc.findings.length}</span>
                          </div>
                          {(svc.service_product || svc.service_version) && (
                            <div className="text-xs text-cyber-text">
                              {svc.service_product} {svc.service_version}
                            </div>
                          )}
                          {svc.findings.map(renderFinding)}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Web Applications */}
                {asset.web_applications.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-cyber-text uppercase mb-2">Web Applications</h4>
                    <div className="space-y-4 pl-4 border-l-2 border-cyber-border ml-2">
                      {asset.web_applications.map(app => (
                        <div key={app.id} className="p-4 bg-cyber-darker border border-cyber-border rounded-lg">
                          <div className="flex justify-between items-start mb-3">
                            <div>
                              <h5 className="text-cyber-accent font-bold mb-1">{app.base_url}</h5>
                              <div className="text-xs text-cyber-text flex gap-4">
                                {app.title && <span>Title: {app.title}</span>}
                                {app.tech_info && <span>Tech: {app.tech_info}</span>}
                              </div>
                            </div>
                            <div className="text-right text-xs text-cyber-text">
                              <div>Endpoints: {app.endpoints.length}</div>
                              <div className="text-red-400">Findings: {app.findings.length}</div>
                            </div>
                          </div>

                          {app.findings.map(renderFinding)}

                          {/* Endpoints */}
                          {app.endpoints.length > 0 && (
                            <div className="mt-4 space-y-2">
                              <h6 className="text-xs font-semibold text-cyber-text uppercase">Endpoints</h6>
                              {app.endpoints.map(ep => (
                                <div key={ep.id} className="p-2 bg-cyber-darkest border border-cyber-border rounded">
                                  <div className="flex justify-between items-center text-sm">
                                    <div className="flex gap-2 items-center">
                                      <span className="text-cyber-text font-mono text-xs">{ep.method || 'ANY'}</span>
                                      <span className="text-cyber-textBright">{ep.path}</span>
                                    </div>
                                    <div className="flex gap-3 text-xs text-cyber-text">
                                      {ep.status_code && <span>{ep.status_code}</span>}
                                      {ep.content_type && <span>{ep.content_type}</span>}
                                      {ep.findings.length > 0 && <span className="text-red-400">F: {ep.findings.length}</span>}
                                    </div>
                                  </div>
                                  {ep.findings.map(renderFinding)}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
