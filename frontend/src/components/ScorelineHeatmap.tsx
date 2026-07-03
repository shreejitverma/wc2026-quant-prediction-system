import React from 'react';

interface ScorelineHeatmapProps {
  matrix: number[][]; // 15x15
  homeTeam: string;
  awayTeam: string;
}

export function ScorelineHeatmap({ matrix, homeTeam, awayTeam }: ScorelineHeatmapProps) {
  // We only show up to 6 goals for practical UI density
  const MAX_GOALS = 6;
  const maxProb = Math.max(...matrix.flat());

  return (
    <div className="flex flex-col items-center">
      <div className="text-sm font-bold mb-2">{homeTeam} vs {awayTeam} Exact Score Probabilities</div>
      <div className="flex">
        <div className="flex flex-col justify-center pr-2 text-xs text-muted-foreground rotate-180" style={{ writingMode: 'vertical-rl' }}>
          {homeTeam} Goals
        </div>
        <div>
          <div className="flex pl-6 pb-1 text-xs text-muted-foreground">
            {awayTeam} Goals
          </div>
          <div className="flex">
            <div className="flex flex-col pr-1">
              {Array.from({ length: MAX_GOALS + 1 }).map((_, i) => (
                <div key={i} className="h-8 w-4 flex items-center justify-end text-xs text-muted-foreground">
                  {i}
                </div>
              ))}
            </div>
            <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${MAX_GOALS + 1}, minmax(0, 1fr))` }}>
              {Array.from({ length: MAX_GOALS + 1 }).map((_, i) => (
                Array.from({ length: MAX_GOALS + 1 }).map((_, j) => {
                  const prob = matrix[i]?.[j] || 0;
                  const intensity = Math.max(0.1, prob / maxProb);
                  return (
                    <div
                      key={`${i}-${j}`}
                      className="h-8 w-8 rounded-sm flex items-center justify-center text-[10px] font-mono group relative"
                      style={{ backgroundColor: `rgba(59, 130, 246, ${intensity})` }}
                    >
                      <span className="opacity-0 group-hover:opacity-100 transition-opacity text-foreground drop-shadow-md z-10">
                        {(prob * 100).toFixed(1)}
                      </span>
                    </div>
                  );
                })
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
