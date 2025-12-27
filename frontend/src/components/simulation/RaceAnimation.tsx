import { useState, useEffect, useCallback, useMemo } from 'react';
import type { AnimationFrame } from '../../types/simulation';
import { RUNNING_STYLE_COLORS } from '../../types/common';
import type { RunningStyle } from '../../types/common';

interface RaceAnimationProps {
  frames: AnimationFrame[];
  distance: number;
  courseType: string;
}

export function RaceAnimation({ frames, distance, courseType }: RaceAnimationProps) {
  const [currentFrameIndex, setCurrentFrameIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);

  const currentFrame = frames[currentFrameIndex];

  // Animation loop
  useEffect(() => {
    if (!isPlaying || !frames.length) return;

    const interval = setInterval(() => {
      setCurrentFrameIndex((prev) => {
        if (prev >= frames.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, 100 / speed);

    return () => clearInterval(interval);
  }, [isPlaying, frames.length, speed]);

  const handlePlay = useCallback(() => {
    if (currentFrameIndex >= frames.length - 1) {
      setCurrentFrameIndex(0);
    }
    setIsPlaying(true);
  }, [currentFrameIndex, frames.length]);

  const handlePause = useCallback(() => {
    setIsPlaying(false);
  }, []);

  const handleReset = useCallback(() => {
    setIsPlaying(false);
    setCurrentFrameIndex(0);
  }, []);

  const handleSliderChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setCurrentFrameIndex(parseInt(e.target.value));
  }, []);

  // Calculate horse positions on the oval track
  const horsePositions = useMemo(() => {
    if (!currentFrame) return [];

    return currentFrame.horses.map((horse) => {
      // Calculate position on oval track
      // progress: 0 = start, 1 = finish
      // The track is an oval, so we map progress to angle
      const angle = horse.progress * 2 * Math.PI - Math.PI / 2; // Start at top

      // Oval dimensions (relative to viewBox)
      const centerX = 400;
      const centerY = 200;
      const radiusX = 300;
      const radiusY = 150;

      // Lane offset (inner lanes closer to center)
      const laneOffset = (horse.lane - 1) * 8;
      const adjustedRadiusX = radiusX - laneOffset;
      const adjustedRadiusY = radiusY - laneOffset;

      const x = centerX + adjustedRadiusX * Math.cos(angle);
      const y = centerY + adjustedRadiusY * Math.sin(angle);

      const style = horse.running_style as RunningStyle;
      const color = RUNNING_STYLE_COLORS[style] || '#8b5cf6';

      return {
        ...horse,
        x,
        y,
        color,
      };
    });
  }, [currentFrame]);

  if (!frames.length) {
    return (
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4">レースアニメーション</h3>
        <p className="text-gray-500">データがありません</p>
      </div>
    );
  }

  const progress = currentFrame?.time || 0;
  const progressPercent = Math.round(progress * 100);

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold mb-2">レースアニメーション</h3>
      <p className="text-sm text-gray-500 mb-4">
        {distance}m {courseType}
      </p>

      {/* Track SVG */}
      <div className="relative bg-gray-100 rounded-lg overflow-hidden">
        <svg viewBox="0 0 800 400" className="w-full h-auto">
          {/* Grass/dirt background */}
          <rect
            x="0"
            y="0"
            width="800"
            height="400"
            fill={courseType === '芝' ? '#86efac' : '#d4a574'}
          />

          {/* Outer track border */}
          <ellipse
            cx="400"
            cy="200"
            rx="350"
            ry="175"
            fill="none"
            stroke="#666"
            strokeWidth="2"
          />

          {/* Track surface */}
          <ellipse
            cx="400"
            cy="200"
            rx="330"
            ry="160"
            fill={courseType === '芝' ? '#22c55e' : '#a8886a'}
          />

          {/* Inner track border */}
          <ellipse
            cx="400"
            cy="200"
            rx="240"
            ry="110"
            fill={courseType === '芝' ? '#86efac' : '#d4a574'}
            stroke="#666"
            strokeWidth="2"
          />

          {/* Corner markers */}
          {[0, 90, 180, 270].map((deg, idx) => {
            const angle = (deg * Math.PI) / 180 - Math.PI / 2;
            const x = 400 + 285 * Math.cos(angle);
            const y = 200 + 135 * Math.sin(angle);
            return (
              <g key={deg}>
                <circle cx={x} cy={y} r="8" fill="#fff" stroke="#666" strokeWidth="1" />
                <text x={x} y={y + 4} textAnchor="middle" fontSize="10" fill="#666">
                  {idx + 1}C
                </text>
              </g>
            );
          })}

          {/* Goal line */}
          <line
            x1="400"
            y1="25"
            x2="400"
            y2="75"
            stroke="#fff"
            strokeWidth="4"
          />
          <text x="400" y="20" textAnchor="middle" fontSize="12" fill="#333" fontWeight="bold">
            GOAL
          </text>

          {/* Horses */}
          {horsePositions.map((horse) => (
            <g key={horse.horse_number}>
              {/* Horse circle */}
              <circle
                cx={horse.x}
                cy={horse.y}
                r="12"
                fill={horse.color}
                stroke="#fff"
                strokeWidth="2"
                style={{
                  transition: 'cx 0.1s linear, cy 0.1s linear',
                }}
              />
              {/* Horse number */}
              <text
                x={horse.x}
                y={horse.y + 4}
                textAnchor="middle"
                fontSize="10"
                fill="#fff"
                fontWeight="bold"
                style={{
                  transition: 'x 0.1s linear, y 0.1s linear',
                }}
              >
                {horse.horse_number}
              </text>
            </g>
          ))}
        </svg>

        {/* Progress indicator */}
        <div className="absolute bottom-2 left-2 right-2 bg-black/50 rounded px-2 py-1">
          <div className="flex items-center justify-between text-white text-xs">
            <span>進行: {progressPercent}%</span>
            <span>
              {progress < 0.2 ? 'スタート' :
               progress < 0.4 ? '1コーナー' :
               progress < 0.6 ? '向こう正面' :
               progress < 0.8 ? '3コーナー' :
               progress < 1.0 ? '直線' : 'ゴール'}
            </span>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="mt-4 space-y-3">
        {/* Playback controls */}
        <div className="flex items-center gap-2">
          {isPlaying ? (
            <button
              onClick={handlePause}
              className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
              </svg>
            </button>
          ) : (
            <button
              onClick={handlePlay}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            </button>
          )}
          <button
            onClick={handleReset}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z" />
            </svg>
          </button>

          {/* Speed control */}
          <div className="flex items-center gap-2 ml-4">
            <span className="text-sm text-gray-600">速度:</span>
            <select
              value={speed}
              onChange={(e) => setSpeed(parseFloat(e.target.value))}
              className="border rounded px-2 py-1 text-sm"
            >
              <option value="0.5">0.5x</option>
              <option value="1">1x</option>
              <option value="2">2x</option>
              <option value="3">3x</option>
            </select>
          </div>
        </div>

        {/* Timeline slider */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 w-12">Start</span>
          <input
            type="range"
            min="0"
            max={frames.length - 1}
            value={currentFrameIndex}
            onChange={handleSliderChange}
            className="flex-1"
          />
          <span className="text-xs text-gray-500 w-12 text-right">Goal</span>
        </div>
      </div>

      {/* Legend */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-500 mb-2">凡例（馬番 + 脚質カラー）:</p>
        <div className="flex flex-wrap gap-2">
          {currentFrame?.horses.slice(0, 8).map((horse) => {
            const style = horse.running_style as RunningStyle;
            const color = RUNNING_STYLE_COLORS[style] || '#8b5cf6';
            return (
              <div
                key={horse.horse_number}
                className="flex items-center gap-1 text-xs"
              >
                <div
                  className="w-4 h-4 rounded-full flex items-center justify-center text-white text-[10px] font-bold"
                  style={{ backgroundColor: color }}
                >
                  {horse.horse_number}
                </div>
                <span className="text-gray-600">{horse.horse_name}</span>
              </div>
            );
          })}
          {(currentFrame?.horses.length || 0) > 8 && (
            <span className="text-xs text-gray-400">+{(currentFrame?.horses.length || 0) - 8}頭</span>
          )}
        </div>
      </div>
    </div>
  );
}
