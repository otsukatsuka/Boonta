import { useState } from 'react';
import type { Entry, EntryUpdate } from '../../types';
import { RunningStyleBadge, WorkoutBadge } from '../common';
import { useUpdateEntry } from '../../hooks';

interface EntryTableProps {
  entries: Entry[];
  onEntryClick?: (entry: Entry) => void;
}

const RUNNING_STYLES = [
  { value: '', label: '-' },
  { value: 'ESCAPE', label: '逃げ' },
  { value: 'FRONT', label: '先行' },
  { value: 'STALKER', label: '差し' },
  { value: 'CLOSER', label: '追込' },
  { value: 'VERSATILE', label: '自在' },
];

export function EntryTable({ entries, onEntryClick }: EntryTableProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editOdds, setEditOdds] = useState('');
  const [editPopularity, setEditPopularity] = useState('');
  const [editRunningStyle, setEditRunningStyle] = useState('');
  const updateEntry = useUpdateEntry();

  // Sort by horse number
  const sortedEntries = [...entries].sort(
    (a, b) => (a.horse_number || 0) - (b.horse_number || 0)
  );

  const handleEditClick = (entry: Entry, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(entry.id);
    setEditOdds(entry.odds?.toString() || '');
    setEditPopularity(entry.popularity?.toString() || '');
    setEditRunningStyle(entry.running_style || '');
  };

  const handleSave = async (entryId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    const data: EntryUpdate = {};

    if (editOdds) {
      const odds = parseFloat(editOdds);
      if (!isNaN(odds) && odds >= 1.0) {
        data.odds = odds;
      }
    }

    if (editPopularity) {
      const popularity = parseInt(editPopularity);
      if (!isNaN(popularity) && popularity >= 1) {
        data.popularity = popularity;
      }
    }

    if (editRunningStyle) {
      data.running_style = editRunningStyle as EntryUpdate['running_style'];
    }

    if (Object.keys(data).length > 0) {
      await updateEntry.mutateAsync({ entryId, data });
    }

    setEditingId(null);
  };

  const handleCancel = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(null);
  };

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
            <th className="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
              編集
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
                {editingId === entry.id ? (
                  <select
                    value={editRunningStyle}
                    onChange={(e) => setEditRunningStyle(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    className="px-1 py-0.5 border rounded text-sm"
                  >
                    {RUNNING_STYLES.map((style) => (
                      <option key={style.value} value={style.value}>
                        {style.label}
                      </option>
                    ))}
                  </select>
                ) : entry.running_style ? (
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
              <td className="px-3 py-4 whitespace-nowrap text-sm text-right">
                {editingId === entry.id ? (
                  <input
                    type="number"
                    step="0.1"
                    min="1"
                    value={editOdds}
                    onChange={(e) => setEditOdds(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    className="w-16 px-1 py-0.5 text-right border rounded text-sm"
                    placeholder="オッズ"
                  />
                ) : (
                  <span className="text-gray-900">
                    {entry.odds ? `${entry.odds.toFixed(1)}` : '-'}
                  </span>
                )}
              </td>
              <td className="px-3 py-4 whitespace-nowrap text-sm text-right">
                {editingId === entry.id ? (
                  <input
                    type="number"
                    min="1"
                    value={editPopularity}
                    onChange={(e) => setEditPopularity(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    className="w-12 px-1 py-0.5 text-right border rounded text-sm"
                    placeholder="人気"
                  />
                ) : (
                  <span
                    className={
                      entry.popularity && entry.popularity <= 3
                        ? 'font-semibold text-primary-600'
                        : 'text-gray-500'
                    }
                  >
                    {entry.popularity || '-'}
                  </span>
                )}
              </td>
              <td className="px-3 py-4 whitespace-nowrap text-center">
                {editingId === entry.id ? (
                  <div className="flex gap-1 justify-center">
                    <button
                      onClick={(e) => handleSave(entry.id, e)}
                      disabled={updateEntry.isPending}
                      className="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
                    >
                      {updateEntry.isPending ? '...' : '保存'}
                    </button>
                    <button
                      onClick={handleCancel}
                      className="px-2 py-1 text-xs bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                    >
                      取消
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={(e) => handleEditClick(entry, e)}
                    className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200"
                  >
                    編集
                  </button>
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
