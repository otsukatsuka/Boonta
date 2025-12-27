import type { StartFormation } from '../../types/simulation';
import { RUNNING_STYLE_COLORS, RUNNING_STYLE_LABELS } from '../../types/common';
import type { RunningStyle } from '../../types/common';

interface StartFormationDiagramProps {
  formation: StartFormation;
}

export function StartFormationDiagram({ formation }: StartFormationDiagramProps) {
  if (!formation.rows.length) {
    return (
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4">隊列予想</h3>
        <p className="text-gray-500">データがありません</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold mb-4">隊列予想</h3>

      {/* Direction indicator */}
      <div className="flex items-center justify-end mb-4 text-sm text-gray-500">
        <span>進行方向</span>
        <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </div>

      <div className="space-y-3">
        {formation.rows.map((row) => (
          <div key={row.row_index} className="flex items-center gap-2">
            {/* Row label */}
            <div className="w-12 text-xs text-gray-500 shrink-0">
              {row.row_label}
            </div>

            {/* Horses in this row */}
            <div className="flex flex-wrap gap-2">
              {row.horses.map((horse) => {
                const style = horse.running_style as RunningStyle;
                const color = RUNNING_STYLE_COLORS[style] || '#8b5cf6';
                const label = RUNNING_STYLE_LABELS[style] || '?';

                return (
                  <div
                    key={horse.horse_number}
                    className="flex items-center gap-1 px-2 py-1 rounded-md text-white text-sm font-medium"
                    style={{ backgroundColor: color }}
                    title={`${horse.horse_name} (${label})`}
                  >
                    <span className="font-bold">{horse.horse_number}</span>
                    <span className="text-xs opacity-80">{label[0]}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex flex-wrap gap-2 text-xs">
          {Object.entries(RUNNING_STYLE_LABELS).map(([key, label]) => (
            <div key={key} className="flex items-center gap-1">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: RUNNING_STYLE_COLORS[key as RunningStyle] }}
              />
              <span className="text-gray-600">{label}</span>
            </div>
          ))}
        </div>
      </div>

      <p className="mt-2 text-xs text-gray-400">
        出走馬: {formation.total_horses}頭
      </p>
    </div>
  );
}
