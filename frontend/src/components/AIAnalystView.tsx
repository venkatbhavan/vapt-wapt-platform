import React, { useState, useEffect } from 'react';
import { ArrowLeft, BrainCircuit, AlertCircle, AlertTriangle, ShieldAlert, CheckCircle2, Search, Loader2 , Link as LinkIcon } from 'lucide-react';
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

      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/assessments/${assessmentId}/ai-analysis`, {
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
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold flex items-center gap-3 text-white">
          <BrainCircuit className="w-8 h-8 text-cyber-accent" />
          <span className="font-mono uppercase tracking-widest">AI Security Analyst</span>
        </h2>
        <button
          onClick={onBack}
          className="border border-cyber-accent text-cyber-accent hover:bg-cyber-accent hover:text-black font-bold uppercase tracking-widest py-2 px-4 rounded transition-colors font-mono text-sm flex items-center gap-2"
        >
          <ArrowLeft size={18} />
          Back
        </button>
      </div>

      <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
        <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
          <Search size={18} className="text-cyber-accent" />
          <h3 className="font-mono text-white tracking-widest uppercase text-sm">NEW ANALYSIS</h3>
        </div>
        <div className="p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-cyber-accent uppercase tracking-wider mb-1">
                Ask the Security Analyst about this assessment's findings, attack surface, compliance, remediation, or risk.
              </label>
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                disabled={loading}
                className="w-full h-24 bg-cyber-dark border border-cyber-border rounded p-3 text-white focus:ring-1 focus:ring-cyber-accent focus:border-cyber-accent outline-none placeholder-cyber-text/50 font-mono text-sm"
                placeholder="E.g., What are the most important security issues in this assessment?"
                maxLength={1000}
              />
              <div className="flex justify-between mt-1">
                <span className="font-mono uppercase text-xs tracking-wider text-cyber-text">
                  Based on assessment evidence. Max 1000 characters.
                </span>
                <span className={`font-mono uppercase text-xs tracking-wider ${question.length >= 1000 ? 'text-red-400' : 'text-cyber-text'}`}>
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
                  className="bg-cyber-dark border border-cyber-border rounded p-2 text-white focus:ring-1 focus:ring-cyber-accent outline-none w-64 font-mono text-sm"
                >
                  {ANALYSIS_TYPES.map(type => (
                    <option key={type.value} value={type.value}>{type.label}</option>
                  ))}
                </select>
              </div>
              <button
                type="submit"
                disabled={loading || !question.trim()}
                className="bg-cyber-accent hover:bg-cyber-accent/80 text-black font-bold uppercase tracking-widest py-2 px-4 rounded transition-colors font-mono text-sm flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
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
            <div className="mt-4 p-4 border border-red-500 bg-red-500/10 rounded flex items-start gap-3 text-red-400">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <p className="font-mono text-sm">{error}</p>
            </div>
          )}
        </div>
      </div>

      {!response && !loading && !error && (
        <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-12 text-center flex flex-col items-center justify-center">
          <BrainCircuit className="w-16 h-16 mb-4 text-cyber-border" />
          <h3 className="text-white font-mono uppercase tracking-widest mb-2">No analysis run yet</h3>
          <p className="text-cyber-text font-mono uppercase text-xs tracking-wider">Enter a question above to have the AI analyze the existing evidence.</p>
        </div>
      )}

      {response && (
        <div className="space-y-6 animate-in fade-in duration-500">
          <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
            <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
              <BrainCircuit size={18} className="text-cyber-accent" />
              <h3 className="font-mono text-white tracking-widest uppercase text-sm">ANALYSIS SUMMARY</h3>
              <span className="ml-auto font-mono uppercase text-xs tracking-wider border border-cyber-accent text-cyber-accent px-2 py-0.5 rounded">
                {response.analyst_version}
              </span>
            </div>
            <div className="p-6">
              <p className="text-cyber-textBright leading-relaxed">
                {response.summary}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
              <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
                <CheckCircle2 size={18} className="text-cyber-accent" />
                <h3 className="font-mono text-white tracking-widest uppercase text-sm">KEY OBSERVATIONS</h3>
              </div>
              <div className="p-6">
                <ul className="space-y-3">
                  {response.key_observations.length > 0 ? (
                    response.key_observations.map((obs, i) => (
                      <li key={i} className="flex gap-3 text-cyber-textBright items-start">
                        <span className="text-cyber-accent mt-1 shrink-0">►</span>
                        <span>{obs}</span>
                      </li>
                    ))
                  ) : (
                    <li className="text-cyber-text font-mono text-sm italic">No key observations.</li>
                  )}
                </ul>
              </div>
            </div>

            <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
              <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
                <AlertTriangle size={18} className="text-cyber-accent" />
                <h3 className="font-mono text-white tracking-widest uppercase text-sm">RISK PRIORITIES</h3>
              </div>
              <div className="p-6">
                <ul className="space-y-3">
                  {response.risk_priorities.length > 0 ? (
                    response.risk_priorities.map((risk, i) => (
                      <li key={i} className="flex gap-3 text-cyber-textBright items-start">
                        <span className="text-cyber-accent mt-1 shrink-0">►</span>
                        <span>{risk}</span>
                      </li>
                    ))
                  ) : (
                    <li className="text-cyber-text font-mono text-sm italic">No explicit risk priorities identified.</li>
                  )}
                </ul>
              </div>
            </div>
          </div>

          <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
            <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
              <LinkIcon size={18} className="text-cyber-accent" />
              <h3 className="font-mono text-white tracking-widest uppercase text-sm">CORRELATIONS</h3>
            </div>
            <div className="p-6">
              <ul className="space-y-3">
                {response.correlations.length > 0 ? (
                  response.correlations.map((corr, i) => (
                    <li key={i} className="flex gap-3 text-cyber-textBright bg-cyber-dark p-4 rounded border border-cyber-border/50 items-start">
                      <span className="text-cyber-accent shrink-0">►</span>
                      <span>{corr}</span>
                    </li>
                  ))
                ) : (
                  <li className="text-cyber-text font-mono text-sm italic">No evidence correlations found.</li>
                )}
              </ul>
            </div>
          </div>

          <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
            <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
              <ShieldAlert size={18} className="text-cyber-accent" />
              <h3 className="font-mono text-white tracking-widest uppercase text-sm">RECOMMENDATIONS</h3>
            </div>
            <div className="p-6">
              <ul className="space-y-3">
                {response.recommendations.length > 0 ? (
                  response.recommendations.map((rec, i) => (
                    <li key={i} className="flex gap-3 text-cyber-textBright items-start">
                      <span className="text-cyber-accent mt-1 shrink-0">►</span>
                      <span>{rec}</span>
                    </li>
                  ))
                ) : (
                  <li className="text-cyber-text font-mono text-sm italic">No recommendations provided.</li>
                )}
              </ul>
              <p className="font-mono uppercase text-xs tracking-wider text-cyber-text mt-6 border-t border-cyber-border/50 pt-4">
                Note: AI recommendations do not replace deterministic platform remediation mappings.
              </p>
            </div>
          </div>

          {response.uncertainties.length > 0 && (
            <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
              <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
                <AlertCircle size={18} className="text-cyber-accent" />
                <h3 className="font-mono text-white tracking-widest uppercase text-sm">UNCERTAINTIES & LIMITATIONS</h3>
              </div>
              <div className="p-6">
                <ul className="space-y-3">
                  {response.uncertainties.map((unc, i) => (
                    <li key={i} className="flex gap-3 text-cyber-textBright items-start">
                      <span className="text-cyber-accent mt-1 shrink-0">►</span>
                      <span>{unc}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {response.evidence_references.length > 0 && (
            <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
              <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
                <Search size={18} className="text-cyber-accent" />
                <h3 className="font-mono text-white tracking-widest uppercase text-sm">EVIDENCE REFERENCES</h3>
              </div>
              <div className="p-6">
                <div className="flex flex-wrap gap-3">
                  {response.evidence_references.map((ref, i) => (
                    <div key={i} className="border border-cyber-border px-2 py-0.5 rounded text-xs font-mono uppercase text-cyber-textBright flex items-center gap-2 bg-cyber-dark">
                      <span className="text-cyber-text">{ref.entity_type}:</span>
                      <span className="text-cyber-accent">{ref.entity_id}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
