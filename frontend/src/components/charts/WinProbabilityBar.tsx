import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

interface WinProbabilityBarProps {
  data: Array<{
    horseName: string;
    probability: number;
  }>;
  maxItems?: number;
}

export function WinProbabilityBar({ data, maxItems = 8 }: WinProbabilityBarProps) {
  const chartData = data
    .slice(0, maxItems)
    .map((item) => ({
      name: item.horseName.length > 6
        ? item.horseName.substring(0, 6) + '...'
        : item.horseName,
      fullName: item.horseName,
      probability: Math.round(item.probability * 100),
    }));

  const getBarColor = (index: number) => {
    if (index === 0) return '#dc2626';
    if (index === 1) return '#2563eb';
    if (index === 2) return '#16a34a';
    return '#9ca3af';
  };

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 60, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 100]}
            tickFormatter={(value) => `${value}%`}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 12 }}
            width={60}
          />
          <Tooltip
            formatter={(value: number) => [`${value}%`, '勝率予測']}
            labelFormatter={(label, payload) => {
              if (payload && payload.length > 0) {
                return payload[0].payload.fullName;
              }
              return label;
            }}
          />
          <Bar dataKey="probability" radius={[0, 4, 4, 0]}>
            {chartData.map((_, index) => (
              <Cell key={`cell-${index}`} fill={getBarColor(index)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
