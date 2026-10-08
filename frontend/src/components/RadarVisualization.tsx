
interface RadarVisualizationProps {
  score: number;
  label: string;
}

export function RadarVisualization({ score, label }: RadarVisualizationProps) {
  const isNoData = score === -1 || score === undefined || Number.isNaN(score);

  return (
    <div className="relative flex items-center justify-center w-64 h-64 mx-auto rounded-full bg-cyber-darker border-4 border-cyber-border overflow-hidden shadow-[0_0_30px_rgba(0,240,255,0.05)]">
      {/* Background Grid */}
      <div className="absolute inset-0 bg-grid-pattern opacity-30"></div>
      
      {/* Radar Sweep */}
      {!isNoData && (
        <div className="absolute inset-0 radar-sweep"></div>
      )}

      {/* Concentric Circles */}
      <div className="absolute inset-4 rounded-full border border-cyber-border/50"></div>
      <div className="absolute inset-12 rounded-full border border-cyber-border/50"></div>
      <div className="absolute inset-20 rounded-full border border-cyber-border/50"></div>
      
      {/* Crosshairs */}
      <div className="absolute w-full h-px bg-cyber-border/50"></div>
      <div className="absolute h-full w-px bg-cyber-border/50"></div>

      {/* Central Value */}
      <div className="relative z-10 flex flex-col items-center justify-center bg-cyber-darkest/80 rounded-full w-32 h-32 backdrop-blur-sm border border-cyber-accent/30 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
        {isNoData ? (
          <span className="text-cyber-text text-sm font-mono text-center px-2">NO DATA</span>
        ) : (
          <>
            <span className="text-4xl font-bold text-cyber-accent font-mono">{score}</span>
            <span className="text-xs font-bold text-cyber-textBright tracking-widest mt-1 uppercase">{label}</span>
          </>
        )}
      </div>
    </div>
  );
}
