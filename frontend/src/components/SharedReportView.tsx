import { useState, useEffect } from 'react';

import { FileText, Clock, AlertTriangle, Target, Shield, Layout, Settings } from 'lucide-react';
import type { ReportDataset, ReportMetadata } from '../types/report';

export function SharedReportView({ token }: { token: string }) {
  
  const [report, setReport] = useState<ReportMetadata | null>(null);
  const [dataset, setDataset] = useState<ReportDataset | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSharedReport = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/shared/reports/${token}`);
        if (!res.ok) throw new Error('Shared report not found or unavailable');
        const data = await res.json();
        setReport(data);
        setDataset(data.snapshot);
      } catch (err: any) {
        setError(err.message || 'Unknown error');
      } finally {
        setLoading(false);
      }
    };
    fetchSharedReport();
  }, [token]);

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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error || !report || !dataset) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950">
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-6 max-w-lg text-center">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">Report Unavailable</h2>
          <p className="text-red-400">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 p-6 md:p-12">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-center justify-between bg-gray-900 border border-gray-800 rounded-lg p-6">
          <div className="flex items-center gap-4">
            <div>
              <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                <FileText className="w-6 h-6 text-blue-400" />
                {report.title}
              </h2>
              <div className="text-sm text-gray-400 flex items-center gap-2 mt-1">
                 <span className="flex items-center gap-1 text-yellow-400 bg-yellow-400/10 px-2 py-0.5 rounded text-xs font-medium border border-yellow-400/20">
                    <Clock className="w-3 h-3" /> Historical report snapshot (Read-Only)
                 </span>
                 {report.generated_at && (
                     <span>Generated: {new Date(report.generated_at).toLocaleString()}</span>
                 )}
              </div>
            </div>
          </div>
        </div>

        {/* Executive Summary */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <h3 className="text-gray-400 text-sm font-medium mb-1">Total Findings</h3>
            <p className="text-3xl font-bold text-white">{dataset.executive_summary.total_findings}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <h3 className="text-purple-400 text-sm font-medium mb-1">Critical Findings</h3>
            <p className="text-3xl font-bold text-purple-500">{dataset.executive_summary.critical_findings}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <h3 className="text-red-400 text-sm font-medium mb-1">High Findings</h3>
            <p className="text-3xl font-bold text-red-500">{dataset.executive_summary.high_findings}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <h3 className="text-blue-400 text-sm font-medium mb-1">Total Assets</h3>
            <p className="text-3xl font-bold text-blue-500">{dataset.executive_summary.total_assets}</p>
          </div>
        </div>

        {/* Scope Overview */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-800">
            <h3 className="text-lg font-medium text-white flex items-center gap-2">
              <Target className="w-5 h-5 text-blue-400" />
              Assessment Scope
            </h3>
          </div>
          <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <p className="text-sm text-gray-500 mb-1">Assessment Name</p>
              <p className="text-white font-medium">{dataset.scope.name}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500 mb-1">Target Overview</p>
              <p className="text-white font-medium">{dataset.scope.target}</p>
            </div>
            <div className="md:col-span-2">
              <p className="text-sm text-gray-500 mb-1">In-Scope Assets</p>
              <pre className="text-sm text-gray-300 bg-gray-950 p-3 rounded-lg border border-gray-800 font-mono">
                {dataset.scope.scope}
              </pre>
            </div>
          </div>
        </div>

        {/* Technical Findings */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-800">
            <h3 className="text-lg font-medium text-white flex items-center gap-2">
              <Shield className="w-5 h-5 text-red-400" />
              Technical Findings
            </h3>
          </div>
          <div className="divide-y divide-gray-800">
            {dataset.technical_findings.length === 0 ? (
              <div className="p-6 text-center text-gray-400">
                No vulnerabilities were identified during this assessment.
              </div>
            ) : (
              dataset.technical_findings.map((finding) => (
                <div key={finding.id} className="p-6 hover:bg-gray-800/50 transition-colors">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h4 className="text-lg font-medium text-white">{finding.title}</h4>
                      <div className="flex items-center gap-3 mt-2 text-sm text-gray-400">
                        <span className="flex items-center gap-1">
                          <Layout className="w-4 h-4" /> {finding.normalized_category}
                        </span>
                        <span className="flex items-center gap-1">
                          <Settings className="w-4 h-4" /> {finding.normalized_type}
                        </span>
                        {finding.location && (
                          <span className="truncate max-w-xs" title={finding.location}>
                            📍 {finding.location}
                          </span>
                        )}
                      </div>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getSeverityColor(finding.severity)}`}>
                      {finding.severity.toUpperCase()}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 bg-gray-950 rounded-lg p-4 border border-gray-800">
                     <div>
                       <span className="text-gray-500 text-xs block mb-1">Risk Score</span>
                       <span className="text-white font-mono">{finding.risk_score.toFixed(1)} / 10.0</span>
                     </div>
                     <div>
                       <span className="text-gray-500 text-xs block mb-1">Confidence</span>
                       <span className="text-white capitalize">{finding.confidence}</span>
                     </div>
                     <div className="md:col-span-2">
                       <span className="text-gray-500 text-xs block mb-1">Root Cause</span>
                       <p className="text-gray-300 text-sm">{finding.root_cause}</p>
                     </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
