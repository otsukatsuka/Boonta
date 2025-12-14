import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

interface RunningStylePieProps {
  data: Record<string, number>;
}

const RUNNING_STYLE_COLORS: Record<string, string> = {
  逃げ: '#ef4444',
  先行: '#f97316',
  差し: '#22c55e',
  追込: '#3b82f6',
};

const RUNNING_STYLE_LABELS: Record<string, string> = {
  逃げ: '逃げ',
  先行: '先行',
  差し: '差し',
  追込: '追込',
};

export function RunningStylePie({ data }: RunningStylePieProps) {
  const chartData = Object.entries(data).map(([name, value]) => ({
    name: RUNNING_STYLE_LABELS[name] || name,
    value,
    color: RUNNING_STYLE_COLORS[name] || '#9ca3af',
  }));

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={40}
            outerRadius={80}
            paddingAngle={2}
            dataKey="value"
            label={({ name, percent }) =>
              `${name} ${((percent ?? 0) * 100).toFixed(0)}%`
            }
            labelLine={false}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number) => [`${value}頭`, '頭数']}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
