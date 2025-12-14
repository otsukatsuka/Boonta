import { useState } from 'react';
import { useRaces } from '../hooks';
import { PageLoading, ErrorMessage, GradeBadge } from '../components/common';
import { RaceCard } from '../components/race';
import type { Grade } from '../types';

export function RaceList() {
  const [gradeFilter, setGradeFilter] = useState<string>('');
  const { data, isLoading, error } = useRaces({
    limit: 50,
    grade: gradeFilter || undefined,
  });

  const grades: Grade[] = ['G1', 'G2', 'G3', 'OP', 'L'];

  if (isLoading) {
    return <PageLoading />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">レース一覧</h1>
        <p className="mt-1 text-gray-500">
          {data ? `${data.total}件のレース` : ''}
        </p>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-gray-500 mr-2">グレード:</span>
          <button
            onClick={() => setGradeFilter('')}
            className={`px-3 py-1 rounded-full text-sm ${
              gradeFilter === ''
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            すべて
          </button>
          {grades.map((grade) => (
            <button
              key={grade}
              onClick={() => setGradeFilter(grade)}
              className={`px-3 py-1 rounded-full text-sm ${
                gradeFilter === grade
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <GradeBadge grade={grade} />
            </button>
          ))}
        </div>
      </div>

      {/* Race List */}
      {error ? (
        <ErrorMessage message="レース情報の取得に失敗しました" />
      ) : data && data.items.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {data.items.map((race) => (
            <RaceCard key={race.id} race={race} />
          ))}
        </div>
      ) : (
        <div className="card text-center text-gray-500 py-8">
          レースがありません
        </div>
      )}
    </div>
  );
}
