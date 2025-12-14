import { useModelStatus, useFeatureImportance } from '../hooks';
import { PageLoading, ErrorMessage } from '../components/common';

export function ModelStatus() {
  const { data: status, isLoading: statusLoading, error: statusError } = useModelStatus();
  const { data: importance, isLoading: importanceLoading } = useFeatureImportance();

  if (statusLoading) {
    return <PageLoading />;
  }

  if (statusError) {
    return <ErrorMessage message="モデル情報の取得に失敗しました" />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">モデル状態</h1>
        <p className="mt-1 text-gray-500">予測モデルの状態と特徴量重要度</p>
      </div>

      {/* Model Status Card */}
      {status && (
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">モデル情報</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <StatusItem
              label="バージョン"
              value={status.model_version}
            />
            <StatusItem
              label="学習状態"
              value={
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    status.is_trained
                      ? 'bg-green-100 text-green-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }`}
                >
                  {status.is_trained ? '学習済み' : '未学習'}
                </span>
              }
            />
            <StatusItem
              label="学習データ数"
              value={`${status.training_data_count.toLocaleString()}件`}
            />
            <StatusItem
              label="最終学習日時"
              value={
                status.last_trained_at
                  ? new Date(status.last_trained_at).toLocaleString('ja-JP')
                  : '-'
              }
            />
          </div>

          {status.metrics && (
            <div className="mt-6 pt-4 border-t border-gray-200">
              <h3 className="text-sm font-medium text-gray-700 mb-2">
                モデル性能指標
              </h3>
              <div className="grid gap-4 md:grid-cols-3">
                {Object.entries(status.metrics).map(([key, value]) => (
                  <div key={key} className="bg-gray-50 rounded-lg p-3">
                    <div className="text-sm text-gray-500">{key}</div>
                    <div className="text-lg font-semibold">
                      {typeof value === 'number' ? value.toFixed(4) : value}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Feature Importance */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">特徴量重要度</h2>
        {importanceLoading ? (
          <div className="text-gray-500">読み込み中...</div>
        ) : importance && importance.features.length > 0 ? (
          <div className="space-y-3">
            {importance.features.map((feature, index) => (
              <FeatureBar
                key={feature.name}
                rank={index + 1}
                name={feature.name}
                importance={feature.importance}
                maxImportance={importance.features[0].importance}
              />
            ))}
          </div>
        ) : (
          <div className="text-gray-500">
            特徴量重要度がありません。モデルを学習してください。
          </div>
        )}
      </div>

      {/* Training Note */}
      <div className="card bg-blue-50 border border-blue-200">
        <h3 className="text-lg font-semibold text-blue-900 mb-2">
          モデル学習について
        </h3>
        <p className="text-blue-800 text-sm">
          モデルの学習は現在CLI経由で行う必要があります。
          AutoGluonを使用して、過去のレースデータから着順予測モデルを構築します。
        </p>
        <pre className="mt-3 p-3 bg-blue-100 rounded text-sm text-blue-900 overflow-x-auto">
          cd backend && python -m app.ml.trainer
        </pre>
      </div>
    </div>
  );
}

interface StatusItemProps {
  label: string;
  value: React.ReactNode;
}

function StatusItem({ label, value }: StatusItemProps) {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <div className="text-sm text-gray-500">{label}</div>
      <div className="text-lg font-semibold mt-1">{value}</div>
    </div>
  );
}

interface FeatureBarProps {
  rank: number;
  name: string;
  importance: number;
  maxImportance: number;
}

function FeatureBar({ rank, name, importance, maxImportance }: FeatureBarProps) {
  const percentage = (importance / maxImportance) * 100;

  // Feature name translations
  const nameMap: Record<string, string> = {
    odds: 'オッズ',
    jockey_win_rate: '騎手勝率',
    avg_position_last5: '直近5走平均着順',
    running_style: '脚質',
    workout_evaluation: '追い切り評価',
    horse_weight: '馬体重',
    distance: '距離',
    venue: '競馬場',
    popularity: '人気',
    win_rate: '勝率',
  };

  return (
    <div className="flex items-center gap-4">
      <div className="w-8 text-sm text-gray-500 text-right">{rank}</div>
      <div className="w-32 text-sm font-medium text-gray-700 truncate">
        {nameMap[name] || name}
      </div>
      <div className="flex-1">
        <div className="h-6 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-primary-500 rounded-full transition-all duration-500"
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
      <div className="w-16 text-sm text-gray-600 text-right">
        {(importance * 100).toFixed(1)}%
      </div>
    </div>
  );
}
