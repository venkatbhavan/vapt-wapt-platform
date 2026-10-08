import { Server, Database, ShieldAlert, Activity } from 'lucide-react';

interface TelemetryStripProps {
  assets: number | string;
  services: number | string;
  findings: number | string;
  risk: number | string;
}

export function TelemetryStrip({ assets, services, findings, risk }: TelemetryStripProps) {
  return (
    <div className="flex flex-wrap border border-cyber-accent/30 rounded bg-cyber-darkest overflow-hidden shadow-[0_0_10px_rgba(0,240,255,0.1)]">
      
      <div className="flex-1 min-w-[120px] flex items-center justify-between p-3 border-r border-cyber-border hover:bg-cyber-darker transition-colors group">
        <div className="flex items-center gap-2">
          <Server size={14} className="text-cyber-accent/70 group-hover:text-cyber-accent transition-colors" />
          <span className="text-[10px] font-mono text-cyber-text uppercase tracking-widest">ASSETS</span>
        </div>
        <span className="font-mono text-white text-sm font-bold animate-fade-in-up">{assets}</span>
      </div>

      <div className="flex-1 min-w-[120px] flex items-center justify-between p-3 border-r border-cyber-border hover:bg-cyber-darker transition-colors group">
        <div className="flex items-center gap-2">
          <Database size={14} className="text-cyber-accent/70 group-hover:text-cyber-accent transition-colors" />
          <span className="text-[10px] font-mono text-cyber-text uppercase tracking-widest">SERVICES</span>
        </div>
        <span className="font-mono text-white text-sm font-bold animate-fade-in-up" style={{ animationDelay: '0.1s' }}>{services}</span>
      </div>

      <div className="flex-1 min-w-[120px] flex items-center justify-between p-3 border-r border-cyber-border hover:bg-cyber-darker transition-colors group">
        <div className="flex items-center gap-2">
          <ShieldAlert size={14} className="text-red-500/70 group-hover:text-red-500 transition-colors" />
          <span className="text-[10px] font-mono text-cyber-text uppercase tracking-widest">FINDINGS</span>
        </div>
        <span className="font-mono text-red-500 text-sm font-bold animate-fade-in-up" style={{ animationDelay: '0.2s' }}>{findings}</span>
      </div>

      <div className="flex-1 min-w-[120px] flex items-center justify-between p-3 hover:bg-cyber-darker transition-colors group">
        <div className="flex items-center gap-2">
          <Activity size={14} className="text-yellow-500/70 group-hover:text-yellow-500 transition-colors" />
          <span className="text-[10px] font-mono text-cyber-text uppercase tracking-widest">RISK</span>
        </div>
        <span className="font-mono text-yellow-500 text-sm font-bold animate-fade-in-up" style={{ animationDelay: '0.3s' }}>{risk}</span>
      </div>

    </div>
  );
}
