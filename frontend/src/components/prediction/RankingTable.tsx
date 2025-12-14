import type { HorsePrediction } from '../../types';

interface RankingTableProps {
  rankings: HorsePrediction[];
}

export function RankingTable({ rankings }: RankingTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              順位
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              馬番
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              馬名
            </th>
            <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">
              スコア
            </th>
            <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">
              勝率
            </th>
            <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">
              複勝率
            </th>
            <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">
              オッズ
            </th>
            <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">
              人気
            </th>
            <th className="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">
              穴馬
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {rankings.map((horse) => (
            <tr
              key={horse.horse_id}
              className={horse.is_dark_horse ? 'bg-yellow-50' : ''}
            >
              <td className="px-3 py-4 whitespace-nowrap">
                <RankBadge rank={horse.rank} />
              </td>
              <td className="px-3 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                {horse.horse_number}
              </td>
              <td className="px-3 py-4 whitespace-nowrap">
                <div className="text-sm font-medium text-gray-900">
                  {horse.horse_name}
                </div>
                {horse.is_dark_horse && horse.dark_horse_reason && (
                  <div className="text-xs text-yellow-600">
                    {horse.dark_horse_reason}
                  </div>
                )}
              </td>
              <td className="px-3 py-4 whitespace-nowrap text-sm text-right">
                <ScoreBar score={horse.score} />
              </td>
              <td className="px-3 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                {(horse.win_probability * 100).toFixed(1)}%
              </td>
              <td className="px-3 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                {(horse.place_probability * 100).toFixed(1)}%
              </td>
              <td className="px-3 py-4 whitespace-nowrap text-sm text-right text-gray-500">
                {horse.odds?.toFixed(1) || '-'}
              </td>
              <td className="px-3 py-4 whitespace-nowrap text-sm text-right text-gray-500">
                {horse.popularity || '-'}
              </td>
              <td className="px-3 py-4 whitespace-nowrap text-center">
                {horse.is_dark_horse && (
                  <span className="text-yellow-500 text-lg">★</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RankBadge({ rank }: { rank: number }) {
  const colors: Record<number, string> = {
    1: 'bg-yellow-400 text-yellow-900',
    2: 'bg-gray-300 text-gray-800',
    3: 'bg-amber-600 text-white',
  };

  return (
    <span
      className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${
        colors[rank] || 'bg-gray-100 text-gray-600'
      }`}
    >
      {rank}
    </span>
  );
}

function ScoreBar({ score }: { score: number }) {
  const percentage = Math.round(score * 100);

  return (
    <div className="flex items-center gap-2">
      <div className="w-20 bg-gray-200 rounded-full h-2">
        <div
          className="bg-primary-500 h-2 rounded-full"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-sm text-gray-700">{percentage}</span>
    </div>
  );
}
