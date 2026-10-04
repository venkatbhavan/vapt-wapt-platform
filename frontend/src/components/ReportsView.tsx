import React, { useState, useEffect } from 'react';
import { ArrowLeft, FileText, CheckCircle, XCircle, Clock, AlertTriangle, ExternalLink, RefreshCw, Shield } from 'lucide-react';
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

  const handleOpenReport = async (reportId: number) => {
    setSelectedReportId(reportId);
    setDatasetLoading(true);
    setDatasetError(null);
    setDataset(null);
    try {
      const res = await fetch('/api/reports/' + reportId + '/dataset');
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
        return <span className="px-2 py-1 bg-gray-500/20 text-gray-400 rounded-full text-xs font-medium flex items-center gap-1"><Clock className="w-3 h-3" /> {status}</span>;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity?.toLowerCase()) {
      case 'critical': return 'text-purple-500 bg-purple-500/10 border-purple-500/20';
      case 'high': return 'text-red-500 bg-red-500/10 border-red-500/20';
      case 'medium': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
      case 'low': return 'text-blue-500 bg-blue-500/10 border-blue-500/20';
      case 'info': return 'text-gray-400 bg-gray-500/10 border-gray-500/20';
      default: return 'text-gray-400 bg-gray-500/10 border-gray-500/20';
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
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 hover:text-white"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                <FileText className="w-6 h-6 text-blue-400" />
                {reportMeta?.title || 'Report Preview'}
              </h2>
              <div className="text-sm text-gray-400 flex items-center gap-2 mt-1">
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
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        ) : datasetError ? (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-6 flex flex-col items-center justify-center text-center">
            <AlertTriangle className="w-12 h-12 text-red-500 mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">Failed to load report dataset</h3>
            <p className="text-gray-400">{datasetError}</p>
          </div>
        ) : dataset ? (
          <div className="space-y-6">
            
            {/* Scope */}
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
              <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
                <Shield className="w-5 h-5 text-gray-400" />
                Assessment Scope
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-gray-800/50 p-4 rounded-lg">
                  <div className="text-sm text-gray-400 mb-1">Name</div>
                  <div className="text-white font-medium">{dataset.scope.name}</div>
                </div>
                <div className="bg-gray-800/50 p-4 rounded-lg">
                  <div className="text-sm text-gray-400 mb-1">Target</div>
                  <div className="text-white font-medium">{dataset.scope.target}</div>
                </div>
                <div className="bg-gray-800/50 p-4 rounded-lg">
                  <div className="text-sm text-gray-400 mb-1">Scope Details</div>
                  <div className="text-white font-medium">{dataset.scope.scope}</div>
                </div>
                <div className="bg-gray-800/50 p-4 rounded-lg">
                  <div className="text-sm text-gray-400 mb-1">Status</div>
                  <div className="text-white font-medium">{dataset.scope.status}</div>
                </div>
              </div>
            </div>

            {/* Executive Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
                   <div className="text-sm text-gray-400 mb-2">Total Findings</div>
                   <div className="text-3xl font-bold text-white">{dataset.executive_summary.total_findings}</div>
                   <div className="mt-4 flex flex-wrap gap-2">
                       <span className={`px-2 py-1 text-xs rounded border ${getSeverityColor("critical")}`}>Critical: {dataset.executive_summary.critical_findings}</span>
                       <span className={`px-2 py-1 text-xs rounded border ${getSeverityColor("high")}`}>High: {dataset.executive_summary.high_findings}</span>
                       <span className={`px-2 py-1 text-xs rounded border ${getSeverityColor("medium")}`}>Medium: {dataset.executive_summary.medium_findings}</span>
                   </div>
                </div>
                <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
                   <div className="text-sm text-gray-400 mb-2">Attack Surface</div>
                   <div className="text-3xl font-bold text-white">{dataset.executive_summary.total_assets}</div>
                   <div className="text-sm text-gray-400 mt-1">Assets Discovered</div>
                </div>
                <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
                   <div className="text-sm text-gray-400 mb-2">Retesting</div>
                   <div className="text-3xl font-bold text-white">{dataset.executive_summary.total_retests}</div>
                   <div className="text-sm text-gray-400 mt-1">Total Retests</div>
                   <div className="text-sm text-green-400 mt-1">{dataset.executive_summary.fixed_findings} Fixed</div>
                </div>
                <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
                   <div className="text-sm text-gray-400 mb-2">Remediation</div>
                   <div className="text-3xl font-bold text-white">{dataset.remediation_summary.findings_with_remediation}</div>
                   <div className="text-sm text-gray-400 mt-1">Findings with Remediation</div>
                </div>
            </div>
            
            {/* Additional Breakdowns */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
                <h3 className="text-lg font-medium text-white mb-4">Risk & Confidence</h3>
                <div className="space-y-4">
                    <div>
                        <h4 className="text-sm font-medium text-gray-400 mb-2">Risk Level Distribution</h4>
                        <div className="flex gap-2 flex-wrap">
                            {Object.entries(dataset.risk_summary.risk_level_distribution).map(([level, count]) => (
                                <div key={level} className="bg-gray-800 px-3 py-1.5 rounded text-sm text-gray-300">
                                    <span className="capitalize">{level}</span>: <span className="font-bold text-white">{count}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
              </div>
              <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
                <h3 className="text-lg font-medium text-white mb-4">Compliance Summary</h3>
                <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="bg-gray-800 p-3 rounded">
                        <div className="text-xs text-gray-400">Frameworks</div>
                        <div className="text-xl text-white font-medium">{dataset.compliance_summary.frameworks_represented}</div>
                    </div>
                    <div className="bg-gray-800 p-3 rounded">
                        <div className="text-xs text-gray-400">Mapped Findings</div>
                        <div className="text-xl text-white font-medium">{dataset.compliance_summary.mapped_finding_count}</div>
                    </div>
                </div>
              </div>
            </div>

            {/* Technical Findings Table */}
            <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
              <div className="p-6 border-b border-gray-800">
                <h3 className="text-lg font-medium text-white">Technical Findings</h3>
                <p className="text-sm text-gray-400 mt-1">Detailed breakdown of all findings identified in the assessment scope.</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase tracking-wider bg-gray-800/20">
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
                            <td colSpan={5} className="p-8 text-center text-gray-500">
                                No technical findings recorded in this report snapshot.
                            </td>
                        </tr>
                    ) : (
                        dataset.technical_findings.map((tf: TechnicalFinding) => (
                          <tr key={tf.id} className="hover:bg-gray-800/30 transition-colors">
                            <td className="p-4">
                              <span className={`inline-flex items-center px-2 py-1 rounded border text-xs font-medium capitalize ${getSeverityColor(tf.severity)}`}>
                                {tf.severity}
                              </span>
                            </td>
                            <td className="p-4">
                              <div className="text-sm font-medium text-white">{tf.title}</div>
                              <div className="text-xs text-gray-500 mt-1 flex gap-2">
                                  {tf.scanner_sources.map(s => <span key={s} className="bg-gray-800 px-1.5 py-0.5 rounded">{s}</span>)}
                              </div>
                            </td>
                            <td className="p-4 text-sm text-gray-300 capitalize">{tf.status}</td>
                            <td className="p-4 text-sm text-gray-400">{tf.normalized_category || '-'}</td>
                            <td className="p-4 text-sm text-gray-400 font-mono text-xs">{tf.location || '-'}</td>
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
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 hover:text-white"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <FileText className="w-6 h-6 text-blue-400" />
              Reports
            </h2>
            <p className="text-sm text-gray-400 mt-1">Generated report snapshots for this assessment</p>
          </div>
        </div>
        <button
          onClick={handleGenerateReport}
          disabled={generating}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
        >
          {generating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
          {generating ? 'Generating...' : 'Generate New Report'}
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      ) : error ? (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 flex items-center gap-3 text-red-400">
          <AlertTriangle className="w-5 h-5" />
          <p>{error}</p>
        </div>
      ) : reports.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-12 flex flex-col items-center justify-center text-center">
          <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mb-4">
            <FileText className="w-8 h-8 text-gray-500" />
          </div>
          <h3 className="text-lg font-medium text-white mb-2">No reports generated</h3>
          <p className="text-gray-400 max-w-sm mb-6">
            No reports have been generated for this assessment yet. Generate a report to capture a historical snapshot of the assessment data.
          </p>
          <button
            onClick={handleGenerateReport}
            disabled={generating}
            className="bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Generate First Report
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {reports.map((report) => (
            <div
              key={report.id}
              className="bg-gray-900 border border-gray-800 rounded-lg p-4 flex items-center justify-between hover:border-gray-700 transition-colors"
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
                  <FileText className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <h4 className="text-white font-medium">{report.title}</h4>
                  <div className="text-sm text-gray-400 flex items-center gap-4 mt-1">
                    <span>Created: {new Date(report.created_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {getStatusBadge(report.status)}
                {report.status === 'generated' && (
                  <button
                    onClick={() => handleOpenReport(report.id)}
                    className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 font-medium px-3 py-1.5 rounded-lg hover:bg-blue-500/10 transition-colors"
                  >
                    View Report
                    <ExternalLink className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
