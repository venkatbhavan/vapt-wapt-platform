import React, { useState, useEffect } from 'react';
import { Linkedin, ArrowLeft, FileText, CheckCircle, XCircle, Clock, AlertTriangle, RefreshCw, Shield, Link, X, Copy } from 'lucide-react';
import { ReportMetadata, ReportDataset, TechnicalFinding } from '../types/report';

interface ReportsViewProps {
  assessmentId: number;
  onBack: () => void;
}

export const ReportsView: React.FC<ReportsViewProps> = ({ assessmentId, onBack }) => {
  const [reports, setReports] = useState<ReportMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [dataset, setDataset] = useState<ReportDataset | null>(null);
  const [datasetLoading, setDatasetLoading] = useState(false);
  const [datasetError, setDatasetError] = useState<string | null>(null);

  const [shareModalReportId, setShareModalReportId] = useState<number | null>(null);
  const [shares, setShares] = useState<any[]>([]);
  const [sharesLoading, setSharesLoading] = useState(false);
  const [expirationOption, setExpirationOption] = useState<string>('never');
  const [newShareUrl, setNewShareUrl] = useState<string | null>(null);

  const openShareModal = async (reportId: number) => {
    setShareModalReportId(reportId);
    setNewShareUrl(null);
    setSharesLoading(true);
    setExpirationOption('never');
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}`}/api/reports/${reportId}/shares?assessment_id=${assessmentId}`);
      if (res.ok) {
        setShares(await res.json());
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSharesLoading(false);
    }
  };

  const createShare = async () => {
    try {
      let expiresAt: string | null = null;
      if (expirationOption !== 'never') {
        const d = new Date();
        if (expirationOption === '1h') d.setHours(d.getHours() + 1);
        else if (expirationOption === '24h') d.setHours(d.getHours() + 24);
        else if (expirationOption === '7d') d.setDate(d.getDate() + 7);
        else if (expirationOption === '30d') d.setDate(d.getDate() + 30);
        expiresAt = d.toISOString();
      }
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}`}/api/reports/${shareModalReportId}/shares?assessment_id=${assessmentId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ expires_at: expiresAt })
      });
      if (!res.ok) throw new Error('Share creation failed');
      const data = await res.json();
      setNewShareUrl(`${window.location.origin}${data.share_url}`);
      setShares([data, ...shares]);
    } catch (err) {
      alert("Failed to create share link");
    }
  };

  const revokeShare = async (shareId: number) => {
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}`}/api/shares/${shareId}/revoke?assessment_id=${assessmentId}`, { method: 'POST' });
      if (res.ok) {
        const updated = await res.json();
        setShares(shares.map(s => s.id === shareId ? updated : s));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const [generating, setGenerating] = useState(false);

  const fetchReports = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch('/api/assessments/' + assessmentId + '/reports');
      if (!res.ok) throw new Error('Failed to fetch reports');
      const data = await res.json();
      setReports(data);
    } catch (err: any) {
      setError(err.message || 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, [assessmentId]);

  const handleGenerateReport = async () => {
    try {
      setGenerating(true);
      const res = await fetch('/api/assessments/' + assessmentId + '/reports', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'Assessment Report - ' + new Date().toLocaleDateString() }),
      });
      if (!res.ok) {
          const body = await res.json();
          throw new Error(body.detail || 'Failed to generate report');
      }
      await fetchReports();
    } catch (err: any) {
      alert(err.message || 'Error generating report');
    } finally {
      setGenerating(false);
    }
  };








  const handleExport = async (reportId: number, format: 'html' | 'pdf') => {
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}`}/api/reports/${reportId}/export/${format}?assessment_id=${assessmentId}`);
      if (!res.ok) throw new Error('Export failed');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const disposition = res.headers.get('content-disposition');
      let filename = `report.${format}`;
      if (disposition && disposition.indexOf('filename=') !== -1) {
          filename = disposition.split('filename=')[1].replace(/"/g, '');
      }
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(`Unable to export ${format.toUpperCase()} report.`);
    }
  };



  const handleOpenReport = async (reportId: number) => {
    setSelectedReportId(reportId);
    setDatasetLoading(true);
    setDatasetError(null);
    setDataset(null);
    try {
      const res = await fetch('/api/reports/' + reportId + '/dataset?assessment_id=' + assessmentId);
      if (!res.ok) {
          const body = await res.json();
          throw new Error(body.detail || 'Failed to fetch report dataset');
      }
      const data = await res.json();
      setDataset(data);
    } catch (err: any) {
      setDatasetError(err.message || 'Unknown error fetching dataset');
    } finally {
      setDatasetLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'generated':
        return <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium flex items-center gap-1"><CheckCircle className="w-3 h-3" /> Generated</span>;
      case 'failed':
        return <span className="px-2 py-1 bg-red-500/20 text-red-400 rounded-full text-xs font-medium flex items-center gap-1"><XCircle className="w-3 h-3" /> Failed</span>;
      default:
        return <span className="px-2 py-1 bg-cyber-text/70/20 text-cyber-text rounded-full text-xs font-medium flex items-center gap-1"><Clock className="w-3 h-3" /> {status}</span>;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity?.toLowerCase()) {
      case 'critical': return 'border border-purple-500 px-2 py-0.5 rounded text-xs font-mono uppercase text-purple-500 bg-purple-500/10';
      case 'high': return 'border border-red-500 px-2 py-0.5 rounded text-xs font-mono uppercase text-red-500 bg-red-500/10';
      case 'medium': return 'border border-yellow-500 px-2 py-0.5 rounded text-xs font-mono uppercase text-yellow-500 bg-yellow-500/10';
      case 'low': return 'border border-cyber-accent px-2 py-0.5 rounded text-xs font-mono uppercase text-cyber-accent bg-cyber-accent/10';
      case 'info': return 'border border-cyber-text px-2 py-0.5 rounded text-xs font-mono uppercase text-cyber-text bg-cyber-text/70/10';
      default: return 'border border-cyber-text px-2 py-0.5 rounded text-xs font-mono uppercase text-cyber-text bg-cyber-text/70/10';
    }
  };

  if (selectedReportId) {
    const reportMeta = reports.find(r => r.id === selectedReportId);
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSelectedReportId(null)}
              className="flex items-center gap-2 text-cyber-text hover:text-cyber-accent transition-colors font-mono text-sm uppercase tracking-wider"
            >
              <ArrowLeft size={16} /> BACK
            </button>
            <div>
              <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                <FileText className="w-6 h-6 text-cyber-accent" />
                {reportMeta?.title || 'Report Preview'}
              </h2>
              <div className="font-mono uppercase text-xs tracking-wider text-cyber-text flex items-center gap-2 mt-1">
                 <span className="flex items-center gap-1 text-yellow-400 bg-yellow-400/10 px-2 py-0.5 rounded text-xs font-medium border border-yellow-400/20">
                    <Clock className="w-3 h-3" /> Historical report snapshot
                 </span>
                 {reportMeta?.generated_at && (
                     <span>Generated: {new Date(reportMeta.generated_at).toLocaleString()}</span>
                 )}
              </div>
            </div>
          </div>
        </div>

        {datasetLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyber-accent"></div>
          </div>
        ) : datasetError ? (
          <div className="bg-red-500/10 border border-red-500/20 rounded p-6 flex flex-col items-center justify-center text-center">
            <AlertTriangle className="w-12 h-12 text-red-500 mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">Failed to load report dataset</h3>
            <p className="text-cyber-text">{datasetError}</p>
          </div>
        ) : dataset ? (
          <div className="space-y-6">

            {/* Scope */}
            <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-6">
              <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3"><Shield size={18} className="text-cyber-accent" /><h3 className="font-mono text-white tracking-widest uppercase text-sm">Assessment Scope</h3></div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-cyber-dark/50 p-4 rounded">
                  <div className="font-mono uppercase text-xs tracking-wider text-cyber-text mb-1">Name</div>
                  <div className="text-white font-medium">{dataset.scope.name}</div>
                </div>
                <div className="bg-cyber-dark/50 p-4 rounded">
                  <div className="font-mono uppercase text-xs tracking-wider text-cyber-text mb-1">Target</div>
                  <div className="text-white font-medium">{dataset.scope.target}</div>
                </div>
                <div className="bg-cyber-dark/50 p-4 rounded">
                  <div className="font-mono uppercase text-xs tracking-wider text-cyber-text mb-1">Scope Details</div>
                  <div className="text-white font-medium">{dataset.scope.scope}</div>
                </div>
                <div className="bg-cyber-dark/50 p-4 rounded">
                  <div className="font-mono uppercase text-xs tracking-wider text-cyber-text mb-1">Status</div>
                  <div className="text-white font-medium">{dataset.scope.status}</div>
                </div>
              </div>
            </div>

            {/* Executive Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-6">
                   <div className="font-mono uppercase text-xs tracking-wider text-cyber-text mb-2">Total Findings</div>
                   <div className="text-3xl font-bold text-white">{dataset.executive_summary.total_findings}</div>
                   <div className="mt-4 flex flex-wrap gap-2">
                       <span className={`px-2 py-1 text-xs rounded border ${getSeverityColor("critical")}`}>Critical: {dataset.executive_summary.critical_findings}</span>
                       <span className={`px-2 py-1 text-xs rounded border ${getSeverityColor("high")}`}>High: {dataset.executive_summary.high_findings}</span>
                       <span className={`px-2 py-1 text-xs rounded border ${getSeverityColor("medium")}`}>Medium: {dataset.executive_summary.medium_findings}</span>
                   </div>
                </div>
                <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-6">
                   <div className="font-mono uppercase text-xs tracking-wider text-cyber-text mb-2">Attack Surface</div>
                   <div className="text-3xl font-bold text-white">{dataset.executive_summary.total_assets}</div>
                   <div className="font-mono uppercase text-xs tracking-wider text-cyber-text mt-1">Assets Discovered</div>
                </div>
                <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-6">
                   <div className="font-mono uppercase text-xs tracking-wider text-cyber-text mb-2">Retesting</div>
                   <div className="text-3xl font-bold text-white">{dataset.executive_summary.total_retests}</div>
                   <div className="font-mono uppercase text-xs tracking-wider text-cyber-text mt-1">Total Retests</div>
                   <div className="text-sm text-green-400 mt-1">{dataset.executive_summary.fixed_findings} Fixed</div>
                </div>
                <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-6">
                   <div className="font-mono uppercase text-xs tracking-wider text-cyber-text mb-2">Remediation</div>
                   <div className="text-3xl font-bold text-white">{dataset.remediation_summary.findings_with_remediation}</div>
                   <div className="font-mono uppercase text-xs tracking-wider text-cyber-text mt-1">Findings with Remediation</div>
                </div>
            </div>

            {/* Additional Breakdowns */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-6">
                <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3"><AlertTriangle size={18} className="text-cyber-accent" /><h3 className="font-mono text-white tracking-widest uppercase text-sm">Risk & Confidence</h3></div>
                <div className="space-y-4">
                    <div>
                        <h4 className="text-sm font-medium text-cyber-text mb-2">Risk Level Distribution</h4>
                        <div className="flex gap-2 flex-wrap">
                            {Object.entries(dataset.risk_summary.risk_level_distribution).map(([level, count]) => (
                                <div key={level} className="bg-cyber-dark px-3 py-1.5 rounded text-sm text-cyber-textBright">
                                    <span className="capitalize">{level}</span>: <span className="font-bold text-white">{count}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
              </div>
              <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-6">
                <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3"><CheckCircle size={18} className="text-cyber-accent" /><h3 className="font-mono text-white tracking-widest uppercase text-sm">Compliance Summary</h3></div>
                <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="bg-cyber-dark p-3 rounded">
                        <div className="text-xs text-cyber-text">Frameworks</div>
                        <div className="text-xl text-white font-medium">{dataset.compliance_summary.frameworks_represented}</div>
                    </div>
                    <div className="bg-cyber-dark p-3 rounded">
                        <div className="text-xs text-cyber-text">Mapped Findings</div>
                        <div className="text-xl text-white font-medium">{dataset.compliance_summary.mapped_finding_count}</div>
                    </div>
                </div>
              </div>
            </div>

            {/* Technical Findings Table */}
            <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden overflow-hidden">
              <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3"><FileText size={18} className="text-cyber-accent" /><h3 className="font-mono text-white tracking-widest uppercase text-sm">Technical Findings</h3></div><div className="p-4 bg-cyber-darker"><p className="text-sm text-cyber-text font-mono uppercase text-xs tracking-wider">Detailed breakdown of all findings identified in the assessment scope.</p></div>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-cyber-darkest/50 border-b border-cyber-border text-cyber-text text-xs font-mono uppercase tracking-wider">
                      <th className="p-4 font-medium">Severity</th>
                      <th className="p-4 font-medium">Title</th>
                      <th className="p-4 font-medium">Status</th>
                      <th className="p-4 font-medium">Category</th>
                      <th className="p-4 font-medium">Location</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800">
                    {dataset.technical_findings.length === 0 ? (
                        <tr>
                            <td colSpan={5} className="p-8 text-center text-cyber-text">
                                No technical findings recorded in this report snapshot.
                            </td>
                        </tr>
                    ) : (
                        dataset.technical_findings.map((tf: TechnicalFinding) => (
                          <tr key={tf.id} className="hover:bg-cyber-dark/30 transition-colors">
                            <td className="p-4">
                              <span className={`inline-flex items-center px-2 py-1 rounded border text-xs font-medium capitalize ${getSeverityColor(tf.severity)}`}>
                                {tf.severity}
                              </span>
                            </td>
                            <td className="p-4">
                              <div className="text-sm font-medium text-white">{tf.title}</div>
                              <div className="text-xs text-cyber-text mt-1 flex gap-2">
                                  {tf.scanner_sources.map(s => <span key={s} className="bg-cyber-dark px-1.5 py-0.5 rounded">{s}</span>)}
                              </div>
                            </td>
                            <td className="p-4 text-sm text-cyber-textBright capitalize">{tf.status}</td>
                            <td className="p-4 text-sm text-cyber-text">{tf.normalized_category || '-'}</td>
                            <td className="p-4 text-sm text-cyber-text font-mono text-xs">{tf.location || '-'}</td>
                          </tr>
                        ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    );
  }

  // Reports List View
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="flex items-center gap-2 text-cyber-text hover:text-cyber-accent transition-colors font-mono text-sm uppercase tracking-wider"
          >
            <ArrowLeft size={16} /> BACK
          </button>
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <FileText className="w-6 h-6 text-cyber-accent" />
              Reports
            </h2>
            <p className="text-sm text-cyber-text mt-1">Generated report snapshots for this assessment</p>
          </div>
        </div>
        <button
          onClick={handleGenerateReport}
          disabled={generating}
          className="bg-cyber-accent hover:bg-cyber-accent/80 text-black font-bold uppercase tracking-widest py-2 px-4 rounded transition-colors font-mono text-sm flex items-center gap-2 disabled:opacity-50"
        >
          {generating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
          {generating ? 'Generating...' : 'Generate New Report'}
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyber-accent"></div>
        </div>
      ) : error ? (
        <div className="bg-red-500/10 border border-red-500/20 rounded p-4 flex items-center gap-3 text-red-400">
          <AlertTriangle className="w-5 h-5" />
          <p>{error}</p>
        </div>
      ) : reports.length === 0 ? (
        <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-12 flex flex-col items-center justify-center text-center">
          <div className="w-16 h-16 bg-cyber-dark rounded-full flex items-center justify-center mb-4">
            <FileText className="w-8 h-8 text-cyber-border" />
          </div>
          <h3 className="text-white font-mono uppercase tracking-widest mb-2">No reports generated</h3>
          <p className="text-cyber-text max-w-sm mb-6">
            No reports have been generated for this assessment yet. Generate a report to capture a historical snapshot of the assessment data.
          </p>
          <button
            onClick={handleGenerateReport}
            disabled={generating}
            className="bg-cyber-accent hover:bg-cyber-accent/80 text-black font-bold uppercase tracking-widest py-2 px-4 rounded transition-colors font-mono text-sm flex items-center gap-2"
          >
            Generate First Report
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {reports.map((report) => (
            <div
              key={report.id}
              className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-4 flex items-center justify-between hover:border-cyber-border transition-colors"
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 bg-cyber-accent/10 rounded flex items-center justify-center">
                  <FileText className="w-5 h-5 text-cyber-accent" />
                </div>
                <div>
                  <h4 className="text-white font-medium">{report.title}</h4>
                  <div className="font-mono uppercase text-xs tracking-wider text-cyber-text flex items-center gap-4 mt-1">
                    <span>Created: {new Date(report.created_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {getStatusBadge(report.status)}
                                                  {report.status === 'generated' && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleOpenReport(report.id)}
                        className="flex items-center gap-1 text-sm text-cyber-accent hover:text-cyber-accent font-medium px-3 py-1.5 rounded hover:bg-cyber-accent/10 transition-colors"
                      >
                        View Report
                      </button>
                      <button
                        onClick={() => handleExport(report.id, 'html')}
                        className="flex items-center gap-1 text-sm text-cyber-text hover:text-cyber-textBright font-medium px-3 py-1.5 rounded hover:bg-cyber-dark transition-colors"
                      >
                        HTML
                      </button>
                      <button
                        onClick={() => handleExport(report.id, 'pdf')}
                        className="flex items-center gap-1 text-sm text-cyber-text hover:text-cyber-textBright font-medium px-3 py-1.5 rounded hover:bg-cyber-dark transition-colors"
                      >
                        PDF
                      </button>
                      <button
                        onClick={() => openShareModal(report.id)}
                        className="flex items-center gap-1 text-sm text-cyber-text hover:text-cyber-textBright font-medium px-3 py-1.5 rounded hover:bg-cyber-dark transition-colors"
                      >
                        Share
                      </button>
                    </div>
                  )}
              </div>
            </div>
          ))}
        </div>
      )}

      {shareModalReportId && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden max-w-md w-full p-6 space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-bold text-white flex items-center gap-2">
                <Link className="w-5 h-5 text-cyber-accent" />
                Share Report
              </h3>
              <button onClick={() => setShareModalReportId(null)} className="text-cyber-text hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-6">
              <div>
                <h4 className="text-sm font-medium text-cyber-text mb-3">Existing Share Links</h4>
                {sharesLoading ? (
                  <p className="text-sm text-cyber-text text-center py-4">Loading...</p>
                ) : shares.length === 0 ? (
                  <p className="text-sm text-cyber-text text-center py-4 bg-cyber-darkest border border-cyber-border rounded">No active share links.</p>
                ) : (
                  <div className="space-y-2 max-h-40 overflow-y-auto pr-2">
                    {shares.map(share => (
                      <div key={share.id} className="bg-cyber-darkest border border-cyber-border rounded p-3 flex items-center justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                              share.status === 'active' ? 'bg-green-500/20 text-green-400' :
                              share.status === 'expired' ? 'bg-yellow-500/20 text-yellow-400' :
                              'bg-red-500/20 text-red-400'
                            }`}>
                              {share.status.toUpperCase()}
                            </span>
                            <span className="text-xs text-cyber-text">Views: {share.access_count}</span>
                          </div>
                          <p className="text-xs text-cyber-text mt-1">
                            Expires: {share.expires_at ? new Date(share.expires_at).toLocaleString() : 'Never'}
                          </p>
                        </div>
                        {share.status === 'active' && (
                          <div className="flex gap-2">
                            <button
                              onClick={() => revokeShare(share.id)}
                              className="border border-red-500 text-red-500 hover:bg-red-500 hover:text-white font-bold uppercase tracking-widest py-1 px-2 rounded transition-colors font-mono text-xs"
                            >
                              Revoke
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="pt-4 border-t border-cyber-border">
                <label className="block text-xs font-mono text-cyber-accent uppercase tracking-wider mb-1">Create New Share Link</label>
                <div className="flex items-center gap-2">
                  <select
                    value={expirationOption}
                    onChange={(e) => setExpirationOption(e.target.value)}
                    className="flex-1 bg-cyber-darkest border border-cyber-border rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-cyber-accent"
                  >
                    <option value="never">No expiration</option>
                    <option value="1h">Expires in 1 hour</option>
                    <option value="24h">Expires in 24 hours</option>
                    <option value="7d">Expires in 7 days</option>
                    <option value="30d">Expires in 30 days</option>
                  </select>
                  <button
                    onClick={createShare}
                    className="bg-cyber-accent hover:bg-cyber-accent/80 text-black font-bold uppercase tracking-widest py-2 px-4 rounded transition-colors font-mono text-sm whitespace-nowrap"
                  >
                    Create Link
                  </button>
                </div>
              </div>

              {newShareUrl && (
                <div className="bg-green-500/10 border border-green-500/20 px-4 py-3 rounded flex items-center justify-between">
                  <p className="text-sm text-green-400 font-medium flex items-center gap-2">
                    <CheckCircle className="w-4 h-4" /> Share link created
                  </p>
                  <span className="text-xs text-cyber-text">Ready to share</span>
                </div>
              )}

              <div className="pt-4 border-t border-cyber-border">
                <h4 className="text-sm font-medium text-cyber-text mb-3">Share Externally</h4>
                <div className="flex gap-2">
                  <button 
                    onClick={() => {
                        if (!newShareUrl) {
                            alert("Create a secure share link before sharing externally.");
                            return;
                        }
                        const encoded = encodeURIComponent(newShareUrl);
                        window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${encoded}`, "_blank");
                    }}
                    className="flex-1 flex items-center justify-center gap-2 border border-cyber-accent text-cyber-accent hover:bg-cyber-accent hover:text-black font-bold uppercase tracking-widest py-2 px-4 rounded transition-colors font-mono text-sm"
                  >
                    <Linkedin className="w-4 h-4" /> LinkedIn
                  </button>
                  <button
                    onClick={() => {
                        if (!newShareUrl) {
                            alert("Create a secure share link before sharing externally.");
                            return;
                        }
                        navigator.clipboard.writeText(newShareUrl);
                        alert("Link copied");
                    }}
                    className="flex-1 flex items-center justify-center gap-2 border border-cyber-accent text-cyber-accent hover:bg-cyber-accent hover:text-black font-bold uppercase tracking-widest py-2 px-4 rounded transition-colors font-mono text-sm"
                  >
                    <Copy className="w-4 h-4" /> Copy Link
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
