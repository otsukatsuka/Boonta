import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import type { CornerPositions } from '../../types/simulation';
import { CORNER_LABELS } from '../../types/simulation';
import { RUNNING_STYLE_COLORS } from '../../types/common';
import type { RunningStyle } from '../../types/common';

interface PositionChartProps {
  cornerPositions: CornerPositions[];
  highlightHorses?: number[];
}

// Generate distinct colors for horses
const HORSE_COLORS = [
  '#ef4444', '#f97316', '#eab308', '#22c55e', '#14b8a6',
  '#3b82f6', '#8b5cf6', '#ec4899', '#6b7280', '#0ea5e9',
  '#f43f5e', '#84cc16', '#06b6d4', '#a855f7', '#10b981',
  '#f59e0b', '#6366f1', '#d946ef',
];

export function PositionChart({ cornerPositions, highlightHorses = [] }: PositionChartProps) {
  if (!cornerPositions.length) {
    return (
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4">位置取り推移</h3>
        <p className="text-gray-500">データがありません</p>
      </div>
    );
  }

  // Transform data for Recharts
  // Each corner becomes a data point, each horse becomes a line
  const horses = cornerPositions[0]?.horses || [];
  const horseNumbers = horses.map(h => h.horse_number);

  const chartData = cornerPositions.map(corner => {
    const point: Record<string, number | string> = {
      corner: corner.corner_name,
      cornerLabel: CORNER_LABELS[corner.corner_name] || corner.corner_name,
    };

    corner.horses.forEach(horse => {
      point[`horse_${horse.horse_number}`] = horse.position;
    });

    return point;
  });

  // Get horse names for legend
  const horseInfo = new Map(
    horses.map(h => [
      h.horse_number,
      { name: h.horse_name, style: h.running_style as RunningStyle }
    ])
  );

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold mb-4">位置取り推移</h3>

      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="cornerLabel"
              tick={{ fontSize: 12 }}
            />
            <YAxis
              reversed
              domain={[1, Math.max(...horses.map(() => horseNumbers.length), 18)]}
              tickFormatter={(value) => `${value}位`}
              tick={{ fontSize: 12 }}
            />
            <Tooltip
              formatter={(value: number, name: string) => {
                const horseNum = parseInt(name.replace('horse_', ''));
                const info = horseInfo.get(horseNum);
                return [`${value}位`, `${horseNum}番 ${info?.name || ''}`];
              }}
              labelFormatter={(label) => label as string}
            />
            <Legend
              formatter={(value: string) => {
                const horseNum = parseInt(value.replace('horse_', ''));
                return `${horseNum}番`;
              }}
              wrapperStyle={{ fontSize: 11 }}
            />

            {horseNumbers.map((num, idx) => {
              const info = horseInfo.get(num);
              const isHighlighted = highlightHorses.length === 0 || highlightHorses.includes(num);
              const color = info?.style
                ? RUNNING_STYLE_COLORS[info.style]
                : HORSE_COLORS[idx % HORSE_COLORS.length];

              return (
                <Line
                  key={num}
                  type="monotone"
                  dataKey={`horse_${num}`}
                  name={`horse_${num}`}
                  stroke={color}
                  strokeWidth={isHighlighted ? 2 : 1}
                  strokeOpacity={isHighlighted ? 1 : 0.3}
                  dot={{ fill: color, r: isHighlighted ? 4 : 2 }}
                  activeDot={{ r: 6 }}
                />
              );
            })}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <p className="mt-2 text-xs text-gray-400">
        コーナー毎の予想順位を表示しています（上が前、下が後ろ）
      </p>
    </div>
  );
}
