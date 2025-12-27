import type { ScenarioResult } from '../../types/simulation';
import { PACE_COLORS } from '../../types/prediction';
import { RUNNING_STYLE_LABELS } from '../../types/common';
import type { RunningStyle } from '../../types/common';

interface ScenarioComparisonProps {
  scenarios: ScenarioResult[];
  currentPace: 'slow' | 'middle' | 'high';
}

export function ScenarioComparison({ scenarios, currentPace }: ScenarioComparisonProps) {
  if (!scenarios.length) {
    return (
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4">シナリオ比較</h3>
        <p className="text-gray-500">データがありません</p>
      </div>
    );
  }

  // Sort scenarios: high, middle, slow
  const orderedScenarios = [...scenarios].sort((a, b) => {
    const order = { high: 0, middle: 1, slow: 2 };
    return order[a.pace_type] - order[b.pace_type];
  });

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold mb-4">シナリオ比較</h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {orderedScenarios.map((scenario) => {
          const isCurrentPace = scenario.pace_type === currentPace;
          const paceColor = PACE_COLORS[scenario.pace_type];

          return (
            <div
              key={scenario.pace_type}
              className={`border rounded-lg p-4 ${
                isCurrentPace
                  ? 'border-2 ring-2 ring-offset-2'
                  : 'border-gray-200'
              }`}
              style={{
                borderColor: isCurrentPace ? paceColor : undefined,
                // Use CSS variable for ring color
                ['--tw-ring-color' as string]: isCurrentPace ? paceColor : undefined,
              }}
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-3">
                <span
                  className="px-2 py-1 rounded text-white text-sm font-medium"
                  style={{ backgroundColor: paceColor }}
                >
                  {scenario.pace_label}
                </span>
                <span className="text-sm text-gray-500">
                  {Math.round(scenario.probability * 100)}%
                </span>
              </div>

              {/* Current pace indicator */}
              {isCurrentPace && (
                <div className="mb-3 text-xs text-center py-1 bg-yellow-100 text-yellow-800 rounded">
                  予測ペース
                </div>
              )}

              {/* Description */}
              <p className="text-xs text-gray-600 mb-3">
                {scenario.description}
              </p>

              {/* Advantageous styles */}
              <div className="mb-3">
                <p className="text-xs text-gray-500 mb-1">有利脚質:</p>
                <div className="flex gap-1">
                  {scenario.advantageous_styles.map((style) => (
                    <span
                      key={style}
                      className="px-1.5 py-0.5 bg-green-100 text-green-800 text-xs rounded"
                    >
                      {RUNNING_STYLE_LABELS[style as RunningStyle] || style}
                    </span>
                  ))}
                </div>
              </div>

              {/* Top 5 rankings */}
              <div className="mb-3">
                <p className="text-xs text-gray-500 mb-1">予想上位:</p>
                <ol className="space-y-1">
                  {scenario.rankings.slice(0, 5).map((ranking) => (
                    <li
                      key={ranking.horse_number}
                      className="flex items-center text-sm"
                    >
                      <span className={`w-5 h-5 flex items-center justify-center rounded-full text-xs mr-2 ${
                        ranking.rank === 1 ? 'bg-yellow-400 text-white' :
                        ranking.rank === 2 ? 'bg-gray-300 text-gray-700' :
                        ranking.rank === 3 ? 'bg-amber-600 text-white' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {ranking.rank}
                      </span>
                      <span className="font-medium mr-1">{ranking.horse_number}番</span>
                      <span className="text-gray-600 text-xs truncate">
                        {ranking.horse_name}
                      </span>
                    </li>
                  ))}
                </ol>
              </div>

              {/* Key horses (dark horses) */}
              {scenario.key_horses.length > 0 && (
                <div className="pt-2 border-t border-gray-100">
                  <p className="text-xs text-gray-500 mb-1">注目馬:</p>
                  {scenario.key_horses.map((horse) => (
                    <div
                      key={horse.horse_number}
                      className="flex items-center text-xs text-amber-700 bg-amber-50 px-2 py-1 rounded mt-1"
                    >
                      <span className="mr-1">★</span>
                      <span className="font-medium">{horse.horse_number}番</span>
                      <span className="mx-1">{horse.horse_name}</span>
                      <span className="text-amber-600">- {horse.reason}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <p className="mt-4 text-xs text-gray-400">
        各ペースシナリオでの予想結果を比較しています。発生確率は脚質構成から算出しています。
      </p>
    </div>
  );
}
