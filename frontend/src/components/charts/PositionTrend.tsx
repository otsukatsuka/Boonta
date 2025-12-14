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

interface PositionTrendProps {
  data: Array<{
    raceName: string;
    position: number;
  }>;
  horseName?: string;
}

export function PositionTrend({ data, horseName }: PositionTrendProps) {
  const chartData = data.map((item, index) => ({
    name: item.raceName.length > 8
      ? item.raceName.substring(0, 8) + '...'
      : item.raceName,
    fullName: item.raceName,
    position: item.position,
    index: index + 1,
  }));

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="index"
            tickFormatter={(value) => `${value}走前`}
          />
          <YAxis
            reversed
            domain={[1, 18]}
            ticks={[1, 3, 5, 10, 15, 18]}
            tickFormatter={(value) => `${value}着`}
          />
          <Tooltip
            formatter={(value: number) => [`${value}着`, '着順']}
            labelFormatter={(_, payload) => {
              if (payload && payload.length > 0) {
                return payload[0].payload.fullName;
              }
              return '';
            }}
          />
          {horseName && <Legend formatter={() => horseName} />}
          <Line
            type="monotone"
            dataKey="position"
            stroke="#2563eb"
            strokeWidth={2}
            dot={{ fill: '#2563eb', r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
