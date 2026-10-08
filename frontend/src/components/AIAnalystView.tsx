import React, { useState, useEffect } from 'react';
import { ArrowLeft, BrainCircuit, AlertCircle, AlertTriangle, ShieldAlert, Link as LinkIcon, CheckCircle2, Search, Loader2 } from 'lucide-react';
import { AIAnalystResponse, APIAnalystRequest } from '../types/aiAnalyst';

interface AIAnalystViewProps {
  assessmentId: number;
  onBack: () => void;
}

const ANALYSIS_TYPES = [
  { value: 'general', label: 'General Analysis' },
  { value: 'risk_prioritization', label: 'Risk Prioritization' },
  { value: 'attack_surface', label: 'Attack Surface Analysis' },
  { value: 'correlation', label: 'Finding Correlation' },
  { value: 'remediation', label: 'Remediation Analysis' },
];

export function AIAnalystView({ assessmentId, onBack }: AIAnalystViewProps) {
  const [question, setQuestion] = useState('');
  const [analysisType, setAnalysisType] = useState('general');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<AIAnalystResponse | null>(null);

  // Clear analysis when assessment changes
  useEffect(() => {
    setQuestion('');
    setAnalysisType('general');
    setError(null);
    setResponse(null);
  }, [assessmentId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError(null);
    
    try {
      const payload: APIAnalystRequest = {
        question: question.trim(),
        analysis_type: analysisType,
      };

      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}`}/api/assessments/${assessmentId}/ai-analysis`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        if (res.status === 422) {
          throw new Error('Invalid question format or length limit exceeded.');
        } else if (res.status === 404) {
          throw new Error('Assessment not found.');
        } else {
          const errData = await res.json().catch(() => null);
          throw new Error(errData?.detail || 'An internal error occurred during analysis.');
        }
      }

      const data: AIAnalystResponse = await res.json();
      setResponse(data);
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-cyber-text hover:text-white transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          Back to Dashboard
        </button>
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <BrainCircuit className="w-6 h-6 text-cyber-accent" />
          AI Security Analyst
        </h2>
      </div>

      <div className="bg-cyber-dark border border-cyber-border rounded-lg p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-cyber-textBright mb-2">
              Ask the Security Analyst about this assessment's findings, attack surface, compliance, remediation, or risk.
            </label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={loading}
              className="w-full h-24 bg-cyber-darker border border-cyber-border rounded-lg p-3 text-white focus:ring-2 focus:ring-cyber-accent focus:border-transparent placeholder-cyber-text/70"
              placeholder="E.g., What are the most important security issues in this assessment?"
              maxLength={1000}
            />
            <div className="flex justify-between mt-1">
              <span className="text-xs text-cyber-text">
                Based on assessment evidence. Max 1000 characters.
              </span>
              <span className={`text-xs ${question.length >= 1000 ? 'text-red-400' : 'text-cyber-text'}`}>
                {question.length} / 1000
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex-1">
              <select
                value={analysisType}
                onChange={(e) => setAnalysisType(e.target.value)}
                disabled={loading}
                className="bg-cyber-darker border border-cyber-border rounded-lg p-2 text-white focus:ring-2 focus:ring-cyber-accent outline-none w-64"
              >
                {ANALYSIS_TYPES.map(type => (
                  <option key={type.value} value={type.value}>{type.label}</option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              disabled={loading || !question.trim()}
              className="flex items-center gap-2 px-6 py-2 bg-cyber-dark hover:bg-cyber-border text-cyber-accent border border-cyber-border text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <BrainCircuit className="w-5 h-5" />
                  Run Analysis
                </>
              )}
            </button>
          </div>
        </form>

        {error && (
          <div className="mt-4 p-4 bg-red-900/20 border border-red-500/50 rounded-lg flex items-start gap-3 text-red-200">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <p>{error}</p>
          </div>
        )}
      </div>

      {!response && !loading && !error && (
        <div className="bg-cyber-dark/50 border border-cyber-border rounded-lg p-12 text-center text-cyber-text">
          <BrainCircuit className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg">No analysis run yet.</p>
          <p className="text-sm mt-2">Enter a question above to have the AI analyze the existing evidence.</p>
        </div>
      )}

      {response && (
        <div className="space-y-6 animate-in fade-in duration-500">
          <div className="bg-cyber-dark border border-cyber-border rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-white flex items-center gap-2">
                <Search className="w-5 h-5 text-cyber-accent" />
                Analysis Summary
              </h3>
              <span className="text-xs bg-cyber-accent/20 text-cyber-accent px-2 py-1 rounded">
                {response.analyst_version}
              </span>
            </div>
            <p className="text-cyber-textBright leading-relaxed text-lg">
              {response.summary}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-cyber-dark border border-cyber-border rounded-lg p-6">
              <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-4">
                <CheckCircle2 className="w-5 h-5 text-green-400" />
                Key Observations
              </h3>
              <ul className="space-y-3">
                {response.key_observations.length > 0 ? (
                  response.key_observations.map((obs, i) => (
                    <li key={i} className="flex gap-2 text-cyber-textBright">
                      <span className="text-green-500 mt-1">•</span>
                      <span>{obs}</span>
                    </li>
                  ))
                ) : (
                  <li className="text-cyber-text italic">No key observations.</li>
                )}
              </ul>
            </div>

            <div className="bg-cyber-dark border border-cyber-border rounded-lg p-6">
              <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-4">
                <AlertTriangle className="w-5 h-5 text-red-400" />
                Risk Priorities
              </h3>
              <ul className="space-y-3">
                {response.risk_priorities.length > 0 ? (
                  response.risk_priorities.map((risk, i) => (
                    <li key={i} className="flex gap-2 text-cyber-textBright">
                      <span className="text-red-500 mt-1">•</span>
                      <span>{risk}</span>
                    </li>
                  ))
                ) : (
                  <li className="text-cyber-text italic">No explicit risk priorities identified.</li>
                )}
              </ul>
            </div>
          </div>

          <div className="bg-cyber-dark border border-cyber-border rounded-lg p-6">
            <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-4">
              <LinkIcon className="w-5 h-5 text-cyber-accent" />
              Correlations
            </h3>
            <ul className="space-y-3">
              {response.correlations.length > 0 ? (
                response.correlations.map((corr, i) => (
                  <li key={i} className="flex gap-2 text-cyber-textBright bg-cyber-darker/50 p-3 rounded">
                    <span className="text-cyber-accent mt-0.5">•</span>
                    <span>{corr}</span>
                  </li>
                ))
              ) : (
                <li className="text-cyber-text italic">No evidence correlations found.</li>
              )}
            </ul>
          </div>

          <div className="bg-cyber-dark border border-cyber-border rounded-lg p-6">
            <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-4">
              <ShieldAlert className="w-5 h-5 text-orange-400" />
              Recommendations
            </h3>
            <ul className="space-y-3">
              {response.recommendations.length > 0 ? (
                response.recommendations.map((rec, i) => (
                  <li key={i} className="flex gap-2 text-cyber-textBright">
                    <span className="text-orange-500 mt-1">•</span>
                    <span>{rec}</span>
                  </li>
                ))
              ) : (
                <li className="text-cyber-text italic">No recommendations provided.</li>
              )}
            </ul>
            <p className="text-xs text-cyber-text mt-4 italic">
              Note: AI recommendations do not replace deterministic platform remediation mappings.
            </p>
          </div>

          {response.uncertainties.length > 0 && (
            <div className="bg-yellow-900/10 border border-yellow-700/50 rounded-lg p-6">
              <h3 className="text-lg font-bold text-yellow-500 flex items-center gap-2 mb-4">
                <AlertCircle className="w-5 h-5" />
                Uncertainties & Limitations
              </h3>
              <ul className="space-y-3">
                {response.uncertainties.map((unc, i) => (
                  <li key={i} className="flex gap-2 text-yellow-200/80">
                    <span className="text-yellow-600 mt-1">•</span>
                    <span>{unc}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {response.evidence_references.length > 0 && (
            <div className="bg-cyber-dark border border-cyber-border rounded-lg p-6">
              <h3 className="text-sm font-bold text-cyber-text uppercase tracking-wider mb-4">
                Evidence References
              </h3>
              <div className="flex flex-wrap gap-2">
                {response.evidence_references.map((ref, i) => (
                  <div key={i} className="bg-cyber-darker border border-cyber-border px-3 py-1.5 rounded-full text-xs text-cyber-textBright flex items-center gap-1.5">
                    <span className="text-cyber-text uppercase">{ref.entity_type}:</span>
                    <span className="font-mono text-cyber-accent">{ref.entity_id}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
