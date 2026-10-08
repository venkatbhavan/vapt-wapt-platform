export function ThreatRadar({ scanning = true }: { scanning?: boolean }) {
  return (
    <div className="relative w-48 h-48 mx-auto rounded-full border border-cyber-accent/40 bg-cyber-darkest/50 overflow-hidden flex items-center justify-center">
      {/* Concentric rings */}
      <div className="absolute inset-4 rounded-full border border-cyber-accent/20"></div>
      <div className="absolute inset-10 rounded-full border border-cyber-accent/20"></div>
      <div className="absolute inset-16 rounded-full border border-cyber-accent/20"></div>
      
      {/* Crosshairs */}
      <div className="absolute w-full h-[1px] bg-cyber-accent/20"></div>
      <div className="absolute h-full w-[1px] bg-cyber-accent/20"></div>

      {/* Sweep */}
      {scanning && (
        <div 
          className="absolute inset-0 rounded-full animate-radar origin-center pointer-events-none"
          style={{ 
            background: 'conic-gradient(from 0deg, rgba(0, 240, 255, 0.3) 0deg, transparent 60deg, transparent 360deg)' 
          }}
        ></div>
      )}
      
      {/* Center dot */}
      <div className="w-1 h-1 rounded-full bg-cyber-accent shadow-[0_0_8px_rgba(0,240,255,1)] relative z-10"></div>
      
      {/* Target Blips */}
      <div className="absolute top-1/4 left-1/3 w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse-ring origin-center"></div>
      <div className="absolute bottom-1/3 right-1/4 w-1.5 h-1.5 bg-yellow-500 rounded-full animate-pulse-ring origin-center" style={{ animationDelay: '1s' }}></div>
      <div className="absolute top-1/2 left-3/4 w-1.5 h-1.5 bg-purple-500 rounded-full animate-pulse-ring origin-center" style={{ animationDelay: '2s' }}></div>
      
      {/* Scan Status Label */}
      <div className="absolute bottom-1 bg-cyber-darkest/90 px-1.5 py-0.5 rounded text-[8px] font-mono text-cyber-accent tracking-widest uppercase border border-cyber-accent/30 z-20">
        {scanning ? 'SCANNING...' : 'STANDBY'}
      </div>
    </div>
  );
}
