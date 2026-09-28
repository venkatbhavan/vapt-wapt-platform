import { useState, useEffect } from 'react';
import { Shield, Activity, Database, Server } from 'lucide-react';
import { ProjectsView } from './components/ProjectsView';
import { AssessmentsView } from './components/AssessmentsView';
import { FindingsView } from './components/FindingsView';

function App() {
  const [apiStatus, setApiStatus] = useState<string>('Checking...');
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [selectedAssessmentId, setSelectedAssessmentId] = useState<number | null>(null);

  useEffect(() => {
    fetch('http://localhost:8000/api/health')
      .then(res => res.json())
      .then(data => setApiStatus(data.status === 'ok' ? 'Connected' : 'Error'))
      .catch(() => setApiStatus('Disconnected'));
  }, []);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-200 p-8 font-sans">
      
      {/* Header */}
      <header className="flex justify-between items-center mb-10 pb-4 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <Shield className="text-blue-500" size={32} />
          <h1 className="text-2xl font-bold tracking-tight text-white">Security Intelligence Platform</h1>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${apiStatus === 'Connected' ? 'bg-green-500' : 'bg-red-500'}`}></div>
          <span className="text-sm font-mono text-gray-400">API: {apiStatus}</span>
        </div>
      </header>

      {/* Dashboard Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        
        {/* Card 1 */}
        <div className="bg-gray-900 border border-gray-800 p-6 rounded-lg shadow-sm">
          <div className="flex justify-between items-start mb-4">
            <div>
              <p className="text-sm text-gray-400">Active Assessments</p>
              <h2 className="text-3xl font-bold text-white mt-1">0</h2>
            </div>
            <Activity className="text-gray-500" size={24} />
          </div>
          <p className="text-xs text-blue-400">No authorized scans running</p>
        </div>

        {/* Card 2 */}
        <div className="bg-gray-900 border border-gray-800 p-6 rounded-lg shadow-sm">
          <div className="flex justify-between items-start mb-4">
            <div>
              <p className="text-sm text-gray-400">Total Projects</p>
              <h2 className="text-3xl font-bold text-white mt-1">--</h2>
            </div>
            <Database className="text-gray-500" size={24} />
          </div>
          <p className="text-xs text-gray-500">Manage your projects below</p>
        </div>

        {/* Card 3 */}
        <div className="bg-gray-900 border border-gray-800 p-6 rounded-lg shadow-sm">
          <div className="flex justify-between items-start mb-4">
            <div>
              <p className="text-sm text-gray-400">Critical Findings</p>
              <h2 className="text-3xl font-bold text-red-500 mt-1">0</h2>
            </div>
            <Server className="text-gray-500" size={24} />
          </div>
          <p className="text-xs text-gray-500">Awaiting scan data</p>
        </div>

      </div>

      {/* Main Content Area */}
      <div className="w-full">
        {selectedAssessmentId ? (
          <FindingsView 
            assessmentId={selectedAssessmentId} 
            onBack={() => setSelectedAssessmentId(null)} 
          />
        ) : selectedProjectId ? (
          <AssessmentsView 
            projectId={selectedProjectId} 
            onBack={() => setSelectedProjectId(null)}
            onSelectAssessment={setSelectedAssessmentId}
          />
        ) : (
          <ProjectsView onSelectProject={setSelectedProjectId} />
        )}
      </div>

    </div>
  );
}

export default App;
