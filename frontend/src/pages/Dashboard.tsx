import { Link } from 'react-router-dom';
import { useUpcomingRaces, useModelStatus } from '../hooks';
import { PageLoading, ErrorMessage } from '../components/common';
import { RaceCard } from '../components/race';

export function Dashboard() {
  const { data: races, isLoading: racesLoading, error: racesError } = useUpcomingRaces(5);
  const { data: modelStatus, isLoading: modelLoading } = useModelStatus();

  if (racesLoading) {
    return <PageLoading />;
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">ダッシュボード</h1>
        <p className="mt-1 text-gray-500">競馬予想AIシステム Boonta</p>
      </div>

      {/* Model Status */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">モデル状態</h2>
        {modelLoading ? (
          <div className="text-gray-500">読み込み中...</div>
        ) : modelStatus ? (
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div
                className={`w-3 h-3 rounded-full ${
                  modelStatus.is_trained ? 'bg-green-500' : 'bg-yellow-500'
                }`}
              />
              <span className="text-sm">
                {modelStatus.is_trained ? '学習済み' : '未学習'}
              </span>
            </div>
            <div className="text-sm text-gray-500">
              バージョン: {modelStatus.model_version}
            </div>
            {modelStatus.training_data_count > 0 && (
              <div className="text-sm text-gray-500">
                学習データ: {modelStatus.training_data_count}件
              </div>
            )}
          </div>
        ) : (
          <div className="text-gray-500">モデル情報を取得できません</div>
        )}
      </div>

      {/* Upcoming Races */}
      <div>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">今後のレース</h2>
          <Link to="/races" className="text-sm text-primary-600 hover:underline">
            すべて見る →
          </Link>
        </div>

        {racesError ? (
          <ErrorMessage message="レース情報の取得に失敗しました" />
        ) : races && races.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {races.map((race) => (
              <RaceCard key={race.id} race={race} />
            ))}
          </div>
        ) : (
          <div className="card text-center text-gray-500 py-8">
            今後のレースはありません
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-3">
        <Link to="/races" className="card hover:shadow-lg transition-shadow text-center">
          <div className="text-3xl mb-2">🏇</div>
          <div className="font-medium">レース一覧</div>
          <div className="text-sm text-gray-500">レースを検索・閲覧</div>
        </Link>
        <Link to="/data-input" className="card hover:shadow-lg transition-shadow text-center">
          <div className="text-3xl mb-2">📝</div>
          <div className="font-medium">データ入力</div>
          <div className="text-sm text-gray-500">レース・出走馬を登録</div>
        </Link>
        <Link to="/model" className="card hover:shadow-lg transition-shadow text-center">
          <div className="text-3xl mb-2">🤖</div>
          <div className="font-medium">モデル管理</div>
          <div className="text-sm text-gray-500">予測モデルの状態確認</div>
        </Link>
      </div>
    </div>
  );
}
