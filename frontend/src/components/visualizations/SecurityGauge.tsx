export function SecurityGauge({ score = 0, label = "POSTURE" }: { score: number, label?: string }) {
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  // Score is out of 100
  const dashoffset = circumference - (score / 100) * circumference;

  const getColor = (s: number) => {
    if (s >= 80) return '#22c55e'; // green-500
    if (s >= 60) return '#eab308'; // yellow-500
    if (s >= 40) return '#f97316'; // orange-500
    return '#ef4444'; // red-500
  };

  const strokeColor = getColor(score);

  return (
    <div className="relative flex flex-col items-center justify-center w-32 h-32 mx-auto">
      <svg className="w-24 h-24 transform -rotate-90" viewBox="0 0 100 100">
        <circle 
          cx="50" cy="50" r={radius} 
          fill="none" 
          stroke="rgba(0, 240, 255, 0.1)" 
          strokeWidth="6" 
        />
        <circle 
          cx="50" cy="50" r={radius} 
          fill="none" 
          stroke={strokeColor} 
          strokeWidth="6" 
          strokeDasharray={circumference}
          strokeDashoffset={circumference}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out"
          style={{ strokeDashoffset: dashoffset }}
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center inset-0">
        <span className="text-2xl font-bold font-mono text-white tracking-widest">{score}</span>
      </div>
      <div className="mt-1 text-[10px] font-mono uppercase tracking-widest text-cyber-text text-center border-t border-cyber-border/50 pt-1 w-full">
        {label}
      </div>
    </div>
  );
}
