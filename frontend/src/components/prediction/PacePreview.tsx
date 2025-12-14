import type { PacePrediction, RunningStyle } from '../../types';
import { PACE_LABELS, PACE_COLORS, RUNNING_STYLE_LABELS } from '../../types';

interface PacePreviewProps {
  pace: PacePrediction;
}

export function PacePreview({ pace }: PacePreviewProps) {
  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">ペース予想</h3>

      <div className="flex items-center gap-4 mb-4">
        <div
          className="px-6 py-3 rounded-lg text-white font-bold text-xl"
          style={{ backgroundColor: PACE_COLORS[pace.type] }}
        >
          {PACE_LABELS[pace.type]}ペース
        </div>
        <div className="text-sm text-gray-500">
          信頼度: {(pace.confidence * 100).toFixed(0)}%
        </div>
      </div>

      <p className="text-gray-700 mb-4">{pace.reason}</p>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="text-sm text-gray-500">逃げ馬</div>
          <div className="text-2xl font-bold text-red-500">{pace.escape_count}頭</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="text-sm text-gray-500">先行馬</div>
          <div className="text-2xl font-bold text-orange-500">{pace.front_count}頭</div>
        </div>
      </div>

      <div>
        <div className="text-sm text-gray-500 mb-2">有利な脚質</div>
        <div className="flex gap-2">
          {pace.advantageous_styles.map((style) => (
            <span
              key={style}
              className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium"
            >
              {RUNNING_STYLE_LABELS[style as RunningStyle] || style}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
