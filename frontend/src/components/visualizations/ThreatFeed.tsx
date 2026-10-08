import { ShieldAlert, AlertTriangle, AlertCircle, Info } from 'lucide-react';

interface FeedEvent {
  id: string;
  severity: string;
  title: string;
  timestamp: string;
}

export function ThreatFeed({ events }: { events: FeedEvent[] }) {
  const getIcon = (sev: string) => {
    switch (sev.toLowerCase()) {
      case 'critical': return <ShieldAlert size={14} className="text-purple-500" />;
      case 'high': return <AlertTriangle size={14} className="text-red-500" />;
      case 'medium': return <AlertTriangle size={14} className="text-yellow-500" />;
      case 'low': return <AlertCircle size={14} className="text-cyber-accent" />;
      default: return <Info size={14} className="text-cyber-text" />;
    }
  };

  const getSeverityStyle = (sev: string) => {
    switch (sev.toLowerCase()) {
      case 'critical': return 'text-purple-500 bg-purple-500/10 border-purple-500/30';
      case 'high': return 'text-red-500 bg-red-500/10 border-red-500/30';
      case 'medium': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/30';
      case 'low': return 'text-cyber-accent bg-cyber-accent/10 border-cyber-accent/30';
      default: return 'text-cyber-text bg-cyber-darkest border-cyber-border';
    }
  };

  if (!events || events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 opacity-50">
        <div className="w-1 h-8 bg-cyber-border mb-3 animate-pulse"></div>
        <p className="text-[10px] font-mono uppercase tracking-widest text-cyber-text">AWAITING THREAT TELEMETRY</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {events.map((evt, idx) => (
        <div 
          key={evt.id} 
          className="flex items-center gap-3 p-2 bg-cyber-darkest/50 border border-cyber-border rounded hover:border-cyber-accent/50 transition-colors animate-fade-in-up"
          style={{ animationDelay: `${idx * 0.1}s` }}
        >
          <div className="w-1 h-8 rounded-full" style={{ 
            backgroundColor: evt.severity === 'critical' ? '#a855f7' : 
                             evt.severity === 'high' ? '#ef4444' : 
                             evt.severity === 'medium' ? '#eab308' : '#00f0ff'
          }}></div>
          <div className="flex-1 flex flex-col justify-center min-w-0">
            <div className="flex items-center justify-between mb-1">
              <span className={`text-[9px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded border ${getSeverityStyle(evt.severity)} flex items-center gap-1 w-max`}>
                {getIcon(evt.severity)}
                {evt.severity}
              </span>
              <span className="text-[9px] font-mono text-cyber-text/70">{evt.timestamp}</span>
            </div>
            <p className="text-xs text-white font-mono uppercase truncate">{evt.title}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
