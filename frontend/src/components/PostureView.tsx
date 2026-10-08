import { useState, useEffect } from 'react';
import { ArrowLeft, AlertTriangle, CheckCircle, BarChart2, ShieldAlert } from 'lucide-react';
import { PostureResult } from '../types/posture';
import { RadarVisualization } from './RadarVisualization';

interface PostureViewProps {
  assessmentId: number;
  onBack: () => void;
}

export function PostureView({ assessmentId, onBack }: PostureViewProps) {
  const [posture, setPosture] = useState<PostureResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_BASE_URL || `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}`}/api/assessments/${assessmentId}/posture`)
      .then(res => {
        if (!res.ok) throw new Error('Failed to load posture data');
        return res.json();
      })
      .then(data => {
        setPosture(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [assessmentId]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyber-accent"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
        <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
          <AlertTriangle size={18} className="text-cyber-accent" />
          <h3 className="font-mono text-white tracking-widest uppercase text-sm">Error Loading Posture</h3>
        </div>
        <div className="p-6">
          <p className="text-cyber-textBright mb-4 font-mono uppercase text-xs tracking-wider">{error}</p>
          <button onClick={onBack} className="bg-cyber-accent hover:bg-cyber-accent/80 text-black font-bold uppercase tracking-widest py-2 px-4 rounded transition-colors font-mono text-sm">
            Go Back
          </button>
        </div>
      </div>
    );
  }

  if (!posture) return null;

  const isNoData = posture.level === 'no_data' || posture.score === null;

  return (
    <div>
      <div className="flex items-center gap-4 mb-8">
        <button
          onClick={onBack}
          className="border border-cyber-accent text-cyber-accent hover:bg-cyber-accent hover:text-black font-bold uppercase tracking-widest py-2 px-4 rounded transition-colors font-mono text-sm flex items-center gap-2"
          aria-label="Go back"
        >
          <ArrowLeft size={16} /> BACK
        </button>
        <div>
          <h2 className="text-2xl font-bold text-white font-mono uppercase tracking-widest">Security Posture</h2>
          <p className="font-mono uppercase text-xs tracking-wider text-cyber-text">Methodology v{posture.methodology_version}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {/* Score Card */}
        <div className="md:col-span-1 bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col">
          <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
            <BarChart2 size={18} className="text-cyber-accent" />
            <h3 className="font-mono text-white tracking-widest uppercase text-sm">System Score</h3>
          </div>
          <div className="p-6 flex-grow flex items-center justify-center">
            <RadarVisualization score={posture.score ?? -1} label={posture.level} />
          </div>
        </div>

        {/* Info Cards */}
        <div className="md:col-span-2 grid grid-cols-2 gap-4">
          <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col">
             <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
              <ShieldAlert size={18} className="text-cyber-accent" />
              <h3 className="font-mono text-white tracking-widest uppercase text-sm">Coverage Status</h3>
            </div>
            <div className="p-6 flex-grow">
              <h3 className="text-xl font-bold text-white font-mono uppercase tracking-widest">{posture.coverage_status}</h3>
              {posture.coverage_status === 'unknown' && <p className="font-mono uppercase text-xs tracking-wider text-cyber-text mt-2">No assets detected.</p>}
              {posture.coverage_status === 'limited' && <p className="font-mono uppercase text-xs tracking-wider text-cyber-text mt-2">Assets present, but insufficient data to score.</p>}
            </div>
          </div>
          
          <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col">
             <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
              <CheckCircle size={18} className="text-cyber-accent" />
              <h3 className="font-mono text-white tracking-widest uppercase text-sm">Generated At</h3>
            </div>
            <div className="p-6 flex-grow">
              <h3 className="text-lg font-bold text-white font-mono uppercase tracking-widest">{new Date(posture.generated_at).toLocaleString()}</h3>
            </div>
          </div>
        </div>
      </div>

      {isNoData ? (
        <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden p-12 text-center flex flex-col items-center justify-center">
          <ShieldAlert className="text-cyber-border mb-4" size={48} />
          <h3 className="text-white font-mono uppercase tracking-widest mb-2">Insufficient Coverage</h3>
          <p className="font-mono uppercase text-xs tracking-wider text-cyber-text">Run scans and verify findings to generate security posture insights.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Dimensions */}
          <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
            <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
              <BarChart2 size={18} className="text-cyber-accent" />
              <h3 className="font-mono text-white tracking-widest uppercase text-sm">Impact Dimensions</h3>
            </div>
            
            <div className="p-6 space-y-4">
              {Object.entries(posture.dimensions).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between">
                  <span className="font-mono uppercase text-xs tracking-wider text-cyber-textBright">{key.replace('_', ' ')}</span>
                  <div className="flex items-center gap-3">
                    <div className="w-32 bg-cyber-dark rounded-full h-2 overflow-hidden border border-cyber-border">
                      <div 
                        className={`h-full ${value > 0 ? 'bg-red-500' : 'bg-green-500'}`} 
                        style={{ width: `${Math.min(100, (value / 50) * 100)}%` }}
                      ></div>
                    </div>
                    <span className={`w-12 text-right font-mono text-xs ${value > 0 ? 'text-red-400' : 'text-green-400'}`}>
                      {value > 0 ? `-${value}` : '0'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Contributors */}
          <div className="bg-cyber-darker border border-cyber-border rounded shadow-[0_0_15px_rgba(0,0,0,0.5)] overflow-hidden">
            <div className="bg-cyber-darkest border-b border-cyber-border p-4 flex items-center gap-3">
              <AlertTriangle size={18} className="text-cyber-accent" />
              <h3 className="font-mono text-white tracking-widest uppercase text-sm">Negative Contributors</h3>
            </div>
            
            <div className="p-6">
              {posture.contributors.length === 0 ? (
                <div className="text-center py-8">
                  <CheckCircle size={48} className="mx-auto mb-4 text-cyber-border" />
                  <h3 className="text-white font-mono uppercase tracking-widest mb-2">No Negative Contributors</h3>
                  <p className="font-mono uppercase text-xs tracking-wider text-cyber-text">Your posture is optimal.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {posture.contributors.map((contrib, idx) => (
                    <div key={idx} className="p-4 bg-cyber-dark/50 rounded border border-cyber-border">
                      <div className="flex justify-between items-start mb-2">
                        <span className="border border-cyber-border px-2 py-0.5 rounded text-xs font-mono uppercase text-cyber-text">
                          {contrib.category}
                        </span>
                        <span className="text-red-400 font-mono text-sm">-{contrib.impact} PTS</span>
                      </div>
                      <p className="font-mono uppercase text-xs tracking-wider text-cyber-textBright mb-2">{contrib.reason}</p>
                      <div className="flex justify-between items-center text-xs text-cyber-text font-mono uppercase tracking-wider">
                        <span>Count: {contrib.count}</span>
                        {contrib.related_finding_ids.length > 0 && (
                          <span>Findings: {contrib.related_finding_ids.join(', ')}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
