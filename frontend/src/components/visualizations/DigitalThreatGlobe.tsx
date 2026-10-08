import { useEffect, useState } from 'react';

export function DigitalThreatGlobe() {
  const [nodes, setNodes] = useState<{ id: number; cx: number; cy: number; delay: string; severity: string }[]>([]);
  const [arcs, setArcs] = useState<{ id: number; d: string; delay: string }[]>([]);

  useEffect(() => {
    // Generate deterministic demo nodes inside a circle of r=100
    const newNodes = [];
    const newArcs = [];
    const severities = ['critical', 'high', 'medium', 'info'];
    
    // Create random-looking but deterministic nodes
    for (let i = 0; i < 12; i++) {
      const angle = (i * 30) * (Math.PI / 180);
      const radius = 20 + Math.random() * 70;
      const cx = 100 + Math.cos(angle) * radius;
      const cy = 100 + Math.sin(angle) * radius;
      
      newNodes.push({
        id: i,
        cx,
        cy,
        delay: `${(i * 0.2).toFixed(1)}s`,
        severity: severities[i % severities.length]
      });

      if (i > 0) {
        const prev = newNodes[i - 1];
        // Draw an arc between nodes
        newArcs.push({
          id: i,
          d: `M ${prev.cx} ${prev.cy} Q 100 100 ${cx} ${cy}`,
          delay: `${(i * 0.1).toFixed(1)}s`
        });
      }
    }
    setNodes(newNodes);
    setArcs(newArcs);
  }, []);

  const getSeverityColor = (sev: string) => {
    switch (sev) {
      case 'critical': return '#a855f7'; // purple-500
      case 'high': return '#ef4444'; // red-500
      case 'medium': return '#eab308'; // yellow-500
      default: return '#00f0ff'; // cyber-accent
    }
  };

  return (
    <div className="relative w-64 h-64 mx-auto flex items-center justify-center">
      {/* Background glow */}
      <div className="absolute inset-0 bg-cyber-accent/5 rounded-full blur-2xl"></div>
      
      <svg viewBox="0 0 200 200" className="w-full h-full relative z-10 animate-spin" style={{ animationDuration: '30s', animationTimingFunction: 'linear' }}>
        <defs>
          <radialGradient id="globeGlow" cx="50%" cy="50%" r="50%">
            <stop offset="80%" stopColor="#00f0ff" stopOpacity="0" />
            <stop offset="100%" stopColor="#00f0ff" stopOpacity="0.3" />
          </radialGradient>
        </defs>
        
        {/* Globe Base */}
        <circle cx="100" cy="100" r="98" fill="none" stroke="#00f0ff" strokeWidth="1" strokeOpacity="0.4" />
        <circle cx="100" cy="100" r="98" fill="url(#globeGlow)" />
        
        {/* Lat / Lng Rings */}
        <ellipse cx="100" cy="100" rx="98" ry="30" fill="none" stroke="#00f0ff" strokeWidth="0.5" strokeOpacity="0.3" />
        <ellipse cx="100" cy="100" rx="30" ry="98" fill="none" stroke="#00f0ff" strokeWidth="0.5" strokeOpacity="0.3" />
        
        {/* Threat Arcs */}
        {arcs.map(arc => (
          <path
            key={arc.id}
            d={arc.d}
            fill="none"
            stroke="#00f0ff"
            strokeWidth="0.5"
            strokeOpacity="0.4"
            strokeDasharray="100"
            strokeDashoffset="100"
            className="animate-draw-line"
            style={{ animationDelay: arc.delay, animationIterationCount: 'infinite', animationDuration: '4s' }}
          />
        ))}

        {/* Threat Nodes */}
        {nodes.map(node => (
          <g key={node.id}>
            {/* Ping animation */}
            <circle 
              cx={node.cx} cy={node.cy} r="4" 
              fill="none" 
              stroke={getSeverityColor(node.severity)} 
              strokeWidth="1"
              className="animate-pulse-ring origin-center"
              style={{ transformOrigin: `${node.cx}px ${node.cy}px`, animationDelay: node.delay }}
            />
            {/* Core dot */}
            <circle cx={node.cx} cy={node.cy} r="2" fill={getSeverityColor(node.severity)} />
          </g>
        ))}
      </svg>
      
      {/* Overlay label */}
      <div className="absolute bottom-2 right-2 bg-cyber-darkest/80 border border-cyber-accent/30 px-2 py-0.5 rounded text-[8px] font-mono text-cyber-accent uppercase tracking-widest backdrop-blur z-20">
        SIMULATED TELEMETRY
      </div>
    </div>
  );
}
