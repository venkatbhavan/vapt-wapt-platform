import { useState, useEffect } from 'react';
import { ArrowLeft, AlertTriangle, CheckCircle, BarChart2, ShieldAlert } from 'lucide-react';
import { PostureResult } from '../types/posture';

interface PostureViewProps {
  assessmentId: number;
  onBack: () => void;
}

export function PostureView({ assessmentId, onBack }: PostureViewProps) {
  const [posture, setPosture] = useState<PostureResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch(`http://localhost:8000/api/assessments/${assessmentId}/posture`)
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
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/50 border border-red-500 p-6 rounded-lg">
        <div className="flex items-center gap-3">
          <AlertTriangle className="text-red-500" />
          <h2 className="text-xl font-bold text-white">Error loading posture</h2>
        </div>
        <p className="mt-2 text-gray-300">{error}</p>
        <button onClick={onBack} className="mt-4 bg-gray-800 text-white px-4 py-2 rounded">Go Back</button>
      </div>
    );
  }

  if (!posture) return null;

  const isNoData = posture.level === 'no_data' || posture.score === null;

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'strong': return 'text-green-500';
      case 'good': return 'text-blue-500';
      case 'moderate': return 'text-yellow-500';
      case 'weak': return 'text-orange-500';
      case 'critical': return 'text-red-500';
      case 'no_data': return 'text-gray-500';
      default: return 'text-gray-500';
    }
  };

  const getLevelBgColor = (level: string) => {
    switch (level) {
      case 'strong': return 'bg-green-900/50 border-green-500';
      case 'good': return 'bg-blue-900/50 border-blue-500';
      case 'moderate': return 'bg-yellow-900/50 border-yellow-500';
      case 'weak': return 'bg-orange-900/50 border-orange-500';
      case 'critical': return 'bg-red-900/50 border-red-500';
      case 'no_data': return 'bg-gray-900/50 border-gray-500';
      default: return 'bg-gray-900/50 border-gray-500';
    }
  };

  return (
    <div>
      <div className="flex items-center gap-4 mb-8">
        <button
          onClick={onBack}
          className="p-2 hover:bg-gray-800 rounded-full transition-colors"
          aria-label="Go back"
        >
          <ArrowLeft size={24} />
        </button>
        <div>
          <h2 className="text-2xl font-bold text-white">Security Posture</h2>
          <p className="text-gray-400">Methodology v{posture.methodology_version}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {/* Score Card */}
        <div className={`md:col-span-1 p-6 rounded-lg border flex flex-col items-center justify-center ${getLevelBgColor(posture.level)}`}>
          <p className="text-sm font-semibold uppercase tracking-wider mb-2">Overall Score</p>
          {isNoData ? (
            <div className="text-center">
              <span className="text-4xl font-bold text-gray-500">N/A</span>
              <p className="text-xs text-gray-400 mt-2">Posture Unavailable</p>
            </div>
          ) : (
            <div className="text-center">
              <span className={`text-6xl font-bold ${getLevelColor(posture.level)}`}>{posture.score}</span>
              <span className="text-3xl text-gray-400 font-bold">/100</span>
              <p className={`text-lg font-bold mt-2 uppercase ${getLevelColor(posture.level)}`}>{posture.level}</p>
            </div>
          )}
        </div>

        {/* Info Cards */}
        <div className="md:col-span-2 grid grid-cols-2 gap-4">
          <div className="bg-gray-900 border border-gray-800 p-6 rounded-lg">
            <p className="text-sm text-gray-400 mb-1">Coverage Status</p>
            <h3 className="text-xl font-bold text-white capitalize">{posture.coverage_status}</h3>
            {posture.coverage_status === 'unknown' && <p className="text-xs text-gray-500 mt-2">No assets detected.</p>}
            {posture.coverage_status === 'limited' && <p className="text-xs text-gray-500 mt-2">Assets present, but insufficient data to score.</p>}
          </div>
          
          <div className="bg-gray-900 border border-gray-800 p-6 rounded-lg">
            <p className="text-sm text-gray-400 mb-1">Generated At</p>
            <h3 className="text-lg font-bold text-white">{new Date(posture.generated_at).toLocaleString()}</h3>
          </div>
        </div>
      </div>

      {isNoData ? (
        <div className="bg-gray-900 border border-gray-800 p-8 rounded-lg text-center">
          <ShieldAlert className="mx-auto text-gray-600 mb-4" size={48} />
          <h3 className="text-xl font-bold text-white mb-2">Coverage is currently insufficient to calculate a meaningful posture score.</h3>
          <p className="text-gray-400">Run scans and verify findings to generate security posture insights.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Dimensions */}
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
            <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
              <BarChart2 size={20} className="text-blue-500" />
              Impact Dimensions
            </h3>
            
            <div className="space-y-4">
              {Object.entries(posture.dimensions).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between">
                  <span className="text-gray-300 capitalize">{key.replace('_', ' ')}</span>
                  <div className="flex items-center gap-3">
                    <div className="w-32 bg-gray-800 rounded-full h-2 overflow-hidden">
                      <div 
                        className={`h-full ${value > 0 ? 'bg-red-500' : 'bg-green-500'}`} 
                        style={{ width: `${Math.min(100, (value / 50) * 100)}%` }}
                      ></div>
                    </div>
                    <span className={`w-12 text-right font-mono ${value > 0 ? 'text-red-400' : 'text-green-400'}`}>
                      {value > 0 ? `-${value}` : '0'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Contributors */}
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
            <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
              <AlertTriangle size={20} className="text-orange-500" />
              Negative Contributors
            </h3>
            
            {posture.contributors.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <CheckCircle size={32} className="mx-auto mb-2 text-green-500" />
                <p>No negative contributors identified.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {posture.contributors.map((contrib, idx) => (
                  <div key={idx} className="p-4 bg-gray-800/50 rounded-lg border border-gray-700">
                    <div className="flex justify-between items-start mb-2">
                      <span className="text-xs font-bold uppercase text-gray-400 bg-gray-800 px-2 py-1 rounded">
                        {contrib.category}
                      </span>
                      <span className="text-red-400 font-bold">-{contrib.impact} pts</span>
                    </div>
                    <p className="text-gray-200 text-sm mb-2">{contrib.reason}</p>
                    <div className="flex justify-between items-center text-xs text-gray-500">
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
      )}
    </div>
  );
}
