import type { TrackConditionResult } from '../../types/simulation';

interface TrackConditionComparisonProps {
  scenarios: TrackConditionResult[];
  currentCondition?: string | null;
}

// 馬場状態の色
const TRACK_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  '良': { bg: 'bg-green-50', border: 'border-green-300', text: 'text-green-800' },
  '稍重': { bg: 'bg-yellow-50', border: 'border-yellow-300', text: 'text-yellow-800' },
  '重': { bg: 'bg-orange-50', border: 'border-orange-300', text: 'text-orange-800' },
  '不良': { bg: 'bg-red-50', border: 'border-red-300', text: 'text-red-800' },
};

// 脚質の日本語名
const STYLE_LABELS: Record<string, string> = {
  'ESCAPE': '逃げ',
  'FRONT': '先行',
  'STALKER': '差し',
  'CLOSER': '追込',
  'VERSATILE': '自在',
};

export function TrackConditionComparison({ scenarios, currentCondition }: TrackConditionComparisonProps) {
  if (!scenarios || scenarios.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4">馬場状態別予想</h3>
        <p className="text-gray-500">データがありません</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold mb-4">馬場状態別予想</h3>
      <p className="text-sm text-gray-500 mb-4">
        馬場状態によって有利な馬が変わります。当日の馬場を確認して参考にしてください。
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {scenarios.map((scenario) => {
          const colors = TRACK_COLORS[scenario.track_condition] || TRACK_COLORS['良'];
          const isCurrent = currentCondition === scenario.track_condition;

          return (
            <div
              key={scenario.track_condition}
              className={`rounded-lg border-2 p-4 ${colors.bg} ${colors.border} ${
                isCurrent ? 'ring-2 ring-blue-500' : ''
              }`}
            >
              {/* ヘッダー */}
              <div className="flex items-center justify-between mb-3">
                <span className={`text-lg font-bold ${colors.text}`}>
                  {scenario.track_condition}
                </span>
                {isCurrent && (
                  <span className="text-xs bg-blue-500 text-white px-2 py-0.5 rounded-full">
                    現在
                  </span>
                )}
              </div>

              {/* 説明 */}
              <p className="text-sm text-gray-600 mb-3">{scenario.description}</p>

              {/* 有利脚質 */}
              <div className="flex gap-1 mb-3">
                {scenario.advantageous_styles.slice(0, 2).map((style, idx) => (
                  <span
                    key={style}
                    className={`text-xs px-2 py-0.5 rounded ${
                      idx === 0 ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-700'
                    }`}
                  >
                    {STYLE_LABELS[style] || style}
                    {idx === 0 && '◎'}
                  </span>
                ))}
              </div>

              {/* ランキング */}
              <div className="space-y-1">
                <div className="text-xs text-gray-500 font-medium">上位5頭</div>
                {scenario.rankings.map((ranking, idx) => (
                  <div
                    key={ranking.horse_number}
                    className={`flex items-center justify-between text-sm ${
                      idx === 0 ? 'font-bold' : ''
                    }`}
                  >
                    <span className="flex items-center gap-1">
                      <span className={`w-5 text-center ${idx === 0 ? 'text-yellow-600' : 'text-gray-500'}`}>
                        {idx === 0 ? '◎' : idx === 1 ? '○' : idx === 2 ? '▲' : `${idx + 1}`}
                      </span>
                      <span className="text-gray-800">{ranking.horse_number}</span>
                      <span className="text-gray-600 truncate max-w-[80px]">{ranking.horse_name}</span>
                    </span>
                  </div>
                ))}
              </div>

              {/* 注目馬 */}
              {scenario.key_horses.length > 0 && (
                <div className="mt-3 pt-2 border-t border-gray-200">
                  <div className="text-xs text-gray-500 font-medium mb-1">穴馬注目</div>
                  {scenario.key_horses.map((horse) => (
                    <div key={horse.horse_number} className="text-sm text-orange-700">
                      ★ {horse.horse_number} {horse.horse_name}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
