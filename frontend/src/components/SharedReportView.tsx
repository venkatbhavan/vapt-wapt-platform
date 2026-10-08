import { useState, useEffect } from 'react';
import { Shield, Server, FileText, AlertTriangle, AlertOctagon, Info } from 'lucide-react';
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

    fetch(`http://localhost:8000/api/shared/reports/${token}`)
      .then(res => {
        if (!res.ok) throw new Error("This shared report is unavailable or has expired.");
        return res.json();
      })
      .then(data => {
        if (!data.snapshot) throw new Error("Report data is unavailable.");
        setDataset(data.snapshot);
        setReportTitle(data.title || "Security Assessment Report");
        // Best-effort Open Graph for SPA
        document.title = `Security Assessment Report - ${data.title || 'VAPT Platform'}`;
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
        <div className="bg-cyber-darker border border-red-500/20 p-8 rounded-lg max-w-md w-full text-center space-y-4">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto" />
          <h2 className="text-xl font-bold text-white">Unavailable</h2>
          <p className="text-cyber-text">{error || "Report not found."}</p>
        </div>
      </div>
    );
  }

  const { executive_summary, risk_summary, technical_findings } = dataset;

  const renderSeverityBadge = (severity: string) => {
    const s = severity.toLowerCase();
    let bg = 'bg-cyber-text/70/10 text-cyber-text border-cyber-text/70/20';
    let Icon = Info;
    if (s === 'critical') { bg = 'bg-red-500/10 text-red-400 border-red-500/20'; Icon = AlertOctagon; }
    if (s === 'high') { bg = 'bg-orange-500/10 text-orange-400 border-orange-500/20'; Icon = AlertTriangle; }
    if (s === 'medium') { bg = 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'; Icon = AlertTriangle; }
    if (s === 'low') { bg = 'bg-cyber-accent/10 text-cyber-accent border-cyber-accent/20'; Icon = Info; }
    
    return (
      <span className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${bg}`}>
        <Icon className="w-3.5 h-3.5" />
        {severity.toUpperCase()}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans selection:bg-blue-200">
      <div className="max-w-5xl mx-auto bg-white shadow-xl min-h-screen">
        {/* Header */}
        <header className="bg-[#0f172a] text-white px-10 py-16 text-center space-y-6">
          <div className="flex justify-center mb-6">
            <div className="bg-cyber-dark p-3 rounded-xl shadow-lg">
              <Shield className="w-10 h-10 text-white" />
            </div>
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight">Security Assessment Report</h1>
          <div className="w-24 h-1 bg-cyber-accent mx-auto rounded-full"></div>
          <div className="space-y-2 text-slate-300">
            <p className="text-xl">{reportTitle || 'Comprehensive VAPT Scan'}</p>
            <p className="text-sm font-mono opacity-75">Historical Report Snapshot</p>
          </div>
        </header>

        <main className="p-10 space-y-16">
          
          {/* Executive Summary */}
          <section className="space-y-6">
            <h2 className="text-2xl font-bold border-b border-gray-200 pb-2 text-slate-800 flex items-center gap-2">
              <FileText className="w-6 h-6 text-cyber-accent" /> Executive Summary
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="bg-red-50 border border-red-100 p-4 rounded-xl text-center">
                <div className="text-3xl font-black text-red-600">{executive_summary.critical_findings}</div>
                <div className="text-xs font-semibold text-red-800 uppercase tracking-wide mt-1">Critical</div>
              </div>
              <div className="bg-orange-50 border border-orange-100 p-4 rounded-xl text-center">
                <div className="text-3xl font-black text-orange-600">{executive_summary.high_findings}</div>
                <div className="text-xs font-semibold text-orange-800 uppercase tracking-wide mt-1">High</div>
              </div>
              <div className="bg-yellow-50 border border-yellow-100 p-4 rounded-xl text-center">
                <div className="text-3xl font-black text-yellow-600">{executive_summary.medium_findings}</div>
                <div className="text-xs font-semibold text-yellow-800 uppercase tracking-wide mt-1">Medium</div>
              </div>
              <div className="bg-blue-50 border border-blue-100 p-4 rounded-xl text-center">
                <div className="text-3xl font-black text-cyber-accent">{executive_summary.low_findings}</div>
                <div className="text-xs font-semibold text-blue-800 uppercase tracking-wide mt-1">Low</div>
              </div>
              <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl text-center">
                <div className="text-3xl font-black text-slate-600">{executive_summary.total_findings}</div>
                <div className="text-xs font-semibold text-slate-800 uppercase tracking-wide mt-1">Total</div>
              </div>
            </div>
          </section>

          {/* Risk Summary */}
          {risk_summary && (
            <section className="space-y-6">
              <h2 className="text-2xl font-bold border-b border-gray-200 pb-2 text-slate-800 flex items-center gap-2">
                <AlertTriangle className="w-6 h-6 text-cyber-accent" /> Risk Summary
              </h2>
              <div className="bg-slate-50 p-6 rounded-xl border border-slate-200 flex flex-col md:flex-row items-center gap-8">
                <div className="flex-1 space-y-2">
                  <h3 className="font-semibold text-slate-800">Severity Distribution</h3>
                  <p className="text-sm text-slate-600">Breakdown of risks across the attack surface.</p>
                </div>
                <div className="flex gap-4">
                  {Object.entries(risk_summary.severity_distribution || {}).map(([sev, count]) => (
                    <div key={sev} className="text-center">
                      <div className="text-2xl font-black text-slate-800">{count as number}</div>
                      <div className="text-xs text-slate-500 uppercase">{sev}</div>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          )}

          {/* Attack Surface */}
          <section className="space-y-6">
            <h2 className="text-2xl font-bold border-b border-gray-200 pb-2 text-slate-800 flex items-center gap-2">
              <Server className="w-6 h-6 text-cyber-accent" /> Attack Surface
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
                <div className="text-2xl font-bold text-slate-800">{executive_summary.total_assets}</div>
                <div className="text-sm text-slate-500 font-medium">Assets</div>
              </div>
              <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
                <div className="text-2xl font-bold text-slate-800">{executive_summary.total_network_services}</div>
                <div className="text-sm text-slate-500 font-medium">Services</div>
              </div>
              <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
                <div className="text-2xl font-bold text-slate-800">{executive_summary.total_endpoints}</div>
                <div className="text-sm text-slate-500 font-medium">Endpoints</div>
              </div>
              <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
                <div className="text-2xl font-bold text-slate-800">{executive_summary.total_web_applications}</div>
                <div className="text-sm text-slate-500 font-medium">Web Apps</div>
              </div>
            </div>
          </section>

          {/* Technical Findings */}
          <section className="space-y-6">
            <h2 className="text-2xl font-bold border-b border-gray-200 pb-2 text-slate-800 flex items-center gap-2">
              <Shield className="w-6 h-6 text-cyber-accent" /> Technical Findings
            </h2>
            {technical_findings.length === 0 ? (
              <p className="text-slate-500 italic">No technical findings reported in this snapshot.</p>
            ) : (
              <div className="space-y-4">
                {technical_findings.map((finding: TechnicalFinding, idx: number) => (
                  <div key={idx} className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                    <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <h3 className="font-bold text-lg text-slate-800">{finding.title}</h3>
                        <div className="flex flex-wrap gap-2 text-sm text-slate-500">
                          {finding.normalized_category && <span>Category: <span className="font-medium">{finding.normalized_category}</span></span>}
                          {finding.status && <span>&bull; Status: <span className="font-medium capitalize">{finding.status}</span></span>}
                        </div>
                      </div>
                      <div className="shrink-0">{renderSeverityBadge(finding.severity)}</div>
                    </div>
                    {finding.root_cause && (
                      <div className="px-6 py-4 border-b border-slate-100">
                        <h4 className="text-sm font-semibold text-slate-800 mb-2">Description</h4>
                        <p className="text-sm text-slate-600 whitespace-pre-wrap leading-relaxed">{finding.root_cause}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>

        </main>

        {/* Footer */}
        <footer className="bg-slate-100 text-slate-500 text-center py-8 text-sm mt-12 border-t border-slate-200">
          <p className="font-medium">Generated with VAPT/WAPT Platform</p>
          <p className="mt-1 opacity-75">Confidential Security Assessment Document</p>
        </footer>
      </div>
    </div>
  );
}
