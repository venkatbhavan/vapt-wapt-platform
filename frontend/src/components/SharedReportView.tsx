import { useState, useEffect } from 'react';
import { Shield, Server, FileText, AlertTriangle, Info } from 'lucide-react';
import type { ReportDataset, TechnicalFinding } from '../types/report';

export function SharedReportView() {
  const [dataset, setDataset] = useState<ReportDataset | null>(null);
  const [reportTitle, setReportTitle] = useState("Security Assessment Report");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Extract token from URL path: /shared/reports/:token
    const pathParts = window.location.pathname.split('/');
    const token = pathParts[pathParts.length - 1];

    if (!token) {
      setError("Invalid share link.");
      setLoading(false);
      return;
    }

    fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/shared/reports/${token}`)
      .then(res => {
        if (!res.ok) throw new Error("This shared report is unavailable or has expired.");
        return res.json();
      })
      .then(data => {
        if (!data.snapshot) throw new Error("Report data is unavailable.");
        setDataset(data.snapshot);
        setReportTitle(data.title || "Security Assessment Report");
        // Best-effort Open Graph for SPA
        document.title = `Security Assessment Report - ${data.title || 'VulnSentinel'}`;
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-cyber-darkest flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyber-accent"></div>
      </div>
    );
  }

  if (error || !dataset) {
    return (
      <div className="min-h-screen bg-cyber-darkest flex items-center justify-center p-4">
        <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden max-w-md w-full text-center">
          <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center justify-center gap-3">
            <AlertTriangle size={18} className="text-red-500" />
            <h3 className="font-mono text-white tracking-widest uppercase text-sm">Unavailable</h3>
          </div>
          <div className="p-8 space-y-4">
            <AlertTriangle className="w-12 h-12 text-red-500 mx-auto" />
            <p className="text-cyber-text font-mono">{error || "Report not found."}</p>
          </div>
        </div>
      </div>
    );
  }

  const { executive_summary, risk_summary, technical_findings } = dataset;

  const renderSeverityBadge = (severity: string) => {
    const s = severity.toLowerCase();
    let bg = 'border-cyber-text text-cyber-text';
    if (s === 'critical') { bg = 'border-red-500 text-red-500'; }
    if (s === 'high') { bg = 'border-orange-500 text-orange-500'; }
    if (s === 'medium') { bg = 'border-yellow-500 text-yellow-500'; }
    if (s === 'low') { bg = 'border-cyber-accent text-cyber-accent'; }
    
    return (
      <span className={`border px-2 py-0.5 rounded text-xs font-mono uppercase ${bg}`}>
        {severity}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-cyber-darkest text-cyber-text font-sans selection:bg-cyber-accent/20">
      <div className="max-w-5xl mx-auto bg-cyber-dark min-h-screen border-x border-cyber-border">
        {/* Header */}
        <header className="bg-cyber-darker border-b border-cyber-border text-white px-10 py-16 text-center space-y-6">
          <div className="flex justify-center mb-6">
            <div className="bg-cyber-darkest border border-cyber-accent p-3 rounded-xl shadow-[0_0_15px_rgba(0,255,204,0.3)]">
              <Shield className="w-10 h-10 text-cyber-accent" />
            </div>
          </div>
          <h1 className="text-4xl font-mono uppercase tracking-widest font-bold">Security Assessment Report</h1>
          <div className="w-24 h-1 bg-cyber-accent mx-auto rounded-full shadow-[0_0_10px_theme(colors.cyber.accent)]"></div>
          <div className="space-y-2 text-cyber-text">
            <p className="text-xl font-mono uppercase tracking-widest text-white">{reportTitle || 'Comprehensive Security Scan'}</p>
            <p className="text-sm font-mono opacity-75 uppercase tracking-wider">Historical Report Snapshot</p>
          </div>
        </header>

        <main className="p-10 space-y-10">
          
          {/* Executive Summary */}
          <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
            <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
              <FileText size={18} className="text-cyber-accent" />
              <h3 className="font-mono text-white tracking-widest uppercase text-sm">Executive Summary</h3>
            </div>
            <div className="p-6 grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="bg-cyber-darkest border border-red-500/50 p-4 rounded text-center">
                <div className="text-3xl font-mono font-bold text-red-500">{executive_summary.critical_findings}</div>
                <div className="font-mono uppercase text-xs tracking-wider text-red-500/80 mt-1">Critical</div>
              </div>
              <div className="bg-cyber-darkest border border-orange-500/50 p-4 rounded text-center">
                <div className="text-3xl font-mono font-bold text-orange-500">{executive_summary.high_findings}</div>
                <div className="font-mono uppercase text-xs tracking-wider text-orange-500/80 mt-1">High</div>
              </div>
              <div className="bg-cyber-darkest border border-yellow-500/50 p-4 rounded text-center">
                <div className="text-3xl font-mono font-bold text-yellow-500">{executive_summary.medium_findings}</div>
                <div className="font-mono uppercase text-xs tracking-wider text-yellow-500/80 mt-1">Medium</div>
              </div>
              <div className="bg-cyber-darkest border border-cyber-accent/50 p-4 rounded text-center">
                <div className="text-3xl font-mono font-bold text-cyber-accent">{executive_summary.low_findings}</div>
                <div className="font-mono uppercase text-xs tracking-wider text-cyber-accent/80 mt-1">Low</div>
              </div>
              <div className="bg-cyber-darkest border border-cyber-border p-4 rounded text-center">
                <div className="text-3xl font-mono font-bold text-white">{executive_summary.total_findings}</div>
                <div className="font-mono uppercase text-xs tracking-wider text-cyber-text mt-1">Total</div>
              </div>
            </div>
          </div>

          {/* Risk Summary */}
          {risk_summary && (
            <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
              <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
                <AlertTriangle size={18} className="text-cyber-accent" />
                <h3 className="font-mono text-white tracking-widest uppercase text-sm">Risk Summary</h3>
              </div>
              <div className="p-6 flex flex-col md:flex-row items-center gap-8">
                <div className="flex-1 space-y-2">
                  <h4 className="font-mono text-white tracking-widest uppercase text-sm">Severity Distribution</h4>
                  <p className="font-mono text-xs text-cyber-text">Breakdown of risks across the attack surface.</p>
                </div>
                <div className="flex gap-4">
                  {Object.entries(risk_summary.severity_distribution || {}).map(([sev, count]) => (
                    <div key={sev} className="text-center bg-cyber-darkest border border-cyber-border p-3 rounded min-w-[80px]">
                      <div className="text-2xl font-mono font-bold text-white">{count as number}</div>
                      <div className="font-mono uppercase text-xs tracking-wider text-cyber-text mt-1">{sev}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Attack Surface */}
          <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
            <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
              <Server size={18} className="text-cyber-accent" />
              <h3 className="font-mono text-white tracking-widest uppercase text-sm">Attack Surface</h3>
            </div>
            <div className="p-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="bg-cyber-darkest border border-cyber-border p-4 rounded text-center">
                <div className="text-2xl font-mono font-bold text-white">{executive_summary.total_assets}</div>
                <div className="font-mono uppercase text-xs tracking-wider text-cyber-text mt-1">Assets</div>
              </div>
              <div className="bg-cyber-darkest border border-cyber-border p-4 rounded text-center">
                <div className="text-2xl font-mono font-bold text-white">{executive_summary.total_network_services}</div>
                <div className="font-mono uppercase text-xs tracking-wider text-cyber-text mt-1">Services</div>
              </div>
              <div className="bg-cyber-darkest border border-cyber-border p-4 rounded text-center">
                <div className="text-2xl font-mono font-bold text-white">{executive_summary.total_endpoints}</div>
                <div className="font-mono uppercase text-xs tracking-wider text-cyber-text mt-1">Endpoints</div>
              </div>
              <div className="bg-cyber-darkest border border-cyber-border p-4 rounded text-center">
                <div className="text-2xl font-mono font-bold text-white">{executive_summary.total_web_applications}</div>
                <div className="font-mono uppercase text-xs tracking-wider text-cyber-text mt-1">Web Apps</div>
              </div>
            </div>
          </div>

          {/* Technical Findings */}
          <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
            <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
              <Shield size={18} className="text-cyber-accent" />
              <h3 className="font-mono text-white tracking-widest uppercase text-sm">Technical Findings</h3>
            </div>
            <div className="p-6">
              {technical_findings.length === 0 ? (
                <div className="text-center py-12">
                  <Info className="w-12 h-12 text-cyber-border mx-auto mb-4" />
                  <h4 className="text-white font-mono uppercase tracking-widest mb-2">No Findings</h4>
                  <p className="text-cyber-text font-mono text-sm">No technical findings reported in this snapshot.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {technical_findings.map((finding: TechnicalFinding, idx: number) => (
                    <div key={idx} className="bg-cyber-darkest border border-cyber-border rounded overflow-hidden">
                      <div className="p-4 border-b border-cyber-border flex items-start justify-between gap-4">
                        <div className="space-y-2">
                          <h3 className="font-mono text-white font-bold">{finding.title}</h3>
                          <div className="flex flex-wrap gap-3">
                            {finding.normalized_category && <span className="font-mono uppercase text-xs tracking-wider text-cyber-accent">CAT: {finding.normalized_category}</span>}
                            {finding.status && <span className="font-mono uppercase text-xs tracking-wider text-cyber-text">STATUS: {finding.status}</span>}
                          </div>
                        </div>
                        <div className="shrink-0">{renderSeverityBadge(finding.severity)}</div>
                      </div>
                      {finding.root_cause && (
                        <div className="p-4 bg-cyber-darker/50">
                          <h4 className="font-mono uppercase text-xs tracking-wider text-cyber-accent mb-2">Description</h4>
                          <p className="text-sm text-cyber-text font-mono whitespace-pre-wrap leading-relaxed">{finding.root_cause}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

        </main>

        {/* Footer */}
        <footer className="bg-cyber-darker border-t border-cyber-border text-cyber-text text-center py-8 text-sm mt-12">
          <p className="font-mono uppercase tracking-widest text-xs text-cyber-accent">Generated with VulnSentinel</p>
          <p className="mt-2 opacity-75 font-mono text-xs uppercase tracking-wider">Confidential Security Assessment Document</p>
        </footer>
      </div>
    </div>
  );
}
