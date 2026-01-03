import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useRaces, useRegisterRace, useCollectTrainingData } from '../hooks';
import { PageLoading, ErrorMessage, GradeBadge } from '../components/common';
import { RaceCard } from '../components/race';
import type { Grade } from '../types';

export function RaceList() {
  const navigate = useNavigate();
  const [gradeFilter, setGradeFilter] = useState<string>('');
  const [showRegisterForm, setShowRegisterForm] = useState(false);
  const [netkeibaId, setNetkeibaId] = useState('');
  const [fetchRunningStyles, setFetchRunningStyles] = useState(false);
  const [showTrainingForm, setShowTrainingForm] = useState(false);
  const [trainingRaceId, setTrainingRaceId] = useState('');

  const { data, isLoading, error } = useRaces({
    limit: 50,
    grade: gradeFilter || undefined,
  });

  const registerRace = useRegisterRace();
  const collectTrainingData = useCollectTrainingData();

  const grades: Grade[] = ['G1', 'G2', 'G3', 'OP', 'L'];

  const handleRegister = async () => {
    if (!netkeibaId.trim()) return;

    try {
      const result = await registerRace.mutateAsync({
        netkeiba_race_id: netkeibaId.trim(),
        fetch_odds: true,
        fetch_running_styles: fetchRunningStyles,
      });

      if (result.success && result.race_id) {
        alert(`${result.race_name} を登録しました！\n出走馬: ${result.entries_count}頭`);
        setShowRegisterForm(false);
        setNetkeibaId('');
        navigate(`/races/${result.race_id}`);
      }
    } catch (err) {
      console.error('Registration failed:', err);
      alert('レース登録に失敗しました。netkeiba IDを確認してください。');
    }
  };

  const handleCollectTrainingData = async () => {
    if (!trainingRaceId.trim()) return;

    try {
      const result = await collectTrainingData.mutateAsync({
        netkeiba_race_id: trainingRaceId.trim(),
      });

      if (result.success) {
        if (result.records_added > 0) {
          alert(
            `${result.race_name} のデータを追加しました！\n` +
            `追加レコード: ${result.records_added}件\n` +
            `総レコード数: ${result.total_records}件`
          );
        } else {
          alert(`${result.race_name} は既にトレーニングデータに含まれています。`);
        }
        setShowTrainingForm(false);
        setTrainingRaceId('');
      }
    } catch (err) {
      console.error('Training data collection failed:', err);
      alert('データ収集に失敗しました。レースが終了しているか確認してください。');
    }
  };

  if (isLoading) {
    return <PageLoading />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">レース一覧</h1>
          <p className="mt-1 text-gray-500">
            {data ? `${data.total}件のレース` : ''}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => {
              setShowTrainingForm(!showTrainingForm);
              setShowRegisterForm(false);
            }}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
          >
            + 学習データ追加
          </button>
          <button
            onClick={() => {
              setShowRegisterForm(!showRegisterForm);
              setShowTrainingForm(false);
            }}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            + 新規レース登録
          </button>
        </div>
      </div>

      {/* Training Data Collection Form */}
      {showTrainingForm && (
        <div className="card border-2 border-purple-200 bg-purple-50">
          <h3 className="text-lg font-semibold text-purple-800 mb-4">
            終了レースから学習データを追加
          </h3>
          <p className="text-sm text-gray-600 mb-4">
            終了したレースのnetkeiba IDを入力すると、結果データを学習データとして追加します。
            モデルを再学習するには、データ追加後にスクリプトを実行してください。
          </p>
          <div className="flex flex-col gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                netkeiba レースID
              </label>
              <input
                type="text"
                value={trainingRaceId}
                onChange={(e) => setTrainingRaceId(e.target.value)}
                placeholder="例: 202506050811 (有馬記念2024)"
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                結果が確定しているレースのみ追加できます
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleCollectTrainingData}
                disabled={collectTrainingData.isPending || !trainingRaceId.trim()}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {collectTrainingData.isPending ? '収集中...' : 'データを追加'}
              </button>
              <button
                onClick={() => {
                  setShowTrainingForm(false);
                  setTrainingRaceId('');
                }}
                className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400"
              >
                キャンセル
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Register Form */}
      {showRegisterForm && (
        <div className="card border-2 border-green-200 bg-green-50">
          <h3 className="text-lg font-semibold text-green-800 mb-4">
            netkeibaからレース登録
          </h3>
          <p className="text-sm text-gray-600 mb-4">
            netkeibaのレースIDを入力すると、レース情報・出走馬・オッズを自動取得します。
          </p>
          <div className="flex flex-col gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                netkeiba レースID
              </label>
              <input
                type="text"
                value={netkeibaId}
                onChange={(e) => setNetkeibaId(e.target.value)}
                placeholder="例: 202606010111 (中山金杯)"
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                URLの race_id= の後ろの12桁の数字
              </p>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="fetchStyles"
                checked={fetchRunningStyles}
                onChange={(e) => setFetchRunningStyles(e.target.checked)}
                className="rounded text-green-600 focus:ring-green-500"
              />
              <label htmlFor="fetchStyles" className="text-sm text-gray-700">
                脚質も取得する（約30秒かかります）
              </label>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleRegister}
                disabled={registerRace.isPending || !netkeibaId.trim()}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {registerRace.isPending ? '登録中...' : 'レースを登録'}
              </button>
              <button
                onClick={() => {
                  setShowRegisterForm(false);
                  setNetkeibaId('');
                }}
                className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400"
              >
                キャンセル
              </button>
            </div>
          </div>
        </div>
      )}

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
