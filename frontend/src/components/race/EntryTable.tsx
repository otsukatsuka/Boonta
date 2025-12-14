import type { Entry } from '../../types';
import { RunningStyleBadge, WorkoutBadge } from '../common';

interface EntryTableProps {
  entries: Entry[];
  onEntryClick?: (entry: Entry) => void;
}

export function EntryTable({ entries, onEntryClick }: EntryTableProps) {
  // Sort by horse number
  const sortedEntries = [...entries].sort(
    (a, b) => (a.horse_number || 0) - (b.horse_number || 0)
  );

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              枠
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              馬番
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              馬名
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              騎手
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              斤量
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              脚質
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              追切
            </th>
            <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              オッズ
            </th>
            <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              人気
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {sortedEntries.map((entry) => (
            <tr
              key={entry.id}
              onClick={() => onEntryClick?.(entry)}
              className={onEntryClick ? 'cursor-pointer hover:bg-gray-50' : ''}
            >
              <td className="px-3 py-4 whitespace-nowrap">
                <PostPositionBox position={entry.post_position} />
              </td>
              <td className="px-3 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                {entry.horse_number}
              </td>
              <td className="px-3 py-4 whitespace-nowrap">
                <div className="text-sm font-medium text-gray-900">
                  {entry.horse_name || '-'}
                </div>
                {entry.horse_weight && (
                  <div className="text-xs text-gray-500">
                    {entry.horse_weight}kg
                    {entry.horse_weight_diff !== null && (
                      <span
                        className={
                          entry.horse_weight_diff > 0
                            ? 'text-red-500'
                            : entry.horse_weight_diff < 0
                            ? 'text-blue-500'
                            : ''
                        }
                      >
                        ({entry.horse_weight_diff > 0 ? '+' : ''}
                        {entry.horse_weight_diff})
                      </span>
                    )}
                  </div>
                )}
              </td>
              <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                {entry.jockey_name || '-'}
              </td>
              <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                {entry.weight || '-'}
              </td>
              <td className="px-3 py-4 whitespace-nowrap">
                {entry.running_style ? (
                  <RunningStyleBadge style={entry.running_style} />
                ) : (
                  <span className="text-gray-400">-</span>
                )}
              </td>
              <td className="px-3 py-4 whitespace-nowrap">
                {entry.workout_evaluation ? (
                  <WorkoutBadge evaluation={entry.workout_evaluation} />
                ) : (
                  <span className="text-gray-400">-</span>
                )}
              </td>
              <td className="px-3 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                {entry.odds ? `${entry.odds.toFixed(1)}` : '-'}
              </td>
              <td className="px-3 py-4 whitespace-nowrap text-sm text-right">
                {entry.popularity ? (
                  <span
                    className={
                      entry.popularity <= 3
                        ? 'font-semibold text-primary-600'
                        : 'text-gray-500'
                    }
                  >
                    {entry.popularity}
                  </span>
                ) : (
                  '-'
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Post position box with colors
function PostPositionBox({ position }: { position: number | null }) {
  if (!position) return <span className="text-gray-400">-</span>;

  const colors: Record<number, string> = {
    1: 'bg-white border-2 border-gray-300',
    2: 'bg-black text-white',
    3: 'bg-red-500 text-white',
    4: 'bg-blue-500 text-white',
    5: 'bg-yellow-400 text-black',
    6: 'bg-green-500 text-white',
    7: 'bg-orange-500 text-white',
    8: 'bg-pink-400 text-white',
  };

  return (
    <span
      className={`inline-flex items-center justify-center w-6 h-6 rounded text-xs font-bold ${
        colors[position] || 'bg-gray-200'
      }`}
    >
      {position}
    </span>
  );
}
