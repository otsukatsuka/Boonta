import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useRace, useRaceEntries, usePrediction, useCreatePrediction, useSimulation, useFetchShutubaOdds } from '../hooks';
import { PageLoading, ErrorMessage, GradeBadge, CourseTypeBadge } from '../components/common';
import { EntryTable } from '../components/race';
import { RankingTable, PacePreview, BetRecommendation } from '../components/prediction';
import { RaceSimulationView } from '../components/simulation';

export function RaceDetail() {
  const { raceId } = useParams<{ raceId: string }>();
  const id = parseInt(raceId || '0', 10);
  const [netkeibaRaceId, setNetkeibaRaceId] = useState('');
  const [showFetchForm, setShowFetchForm] = useState(false);

  const { data: race, isLoading: raceLoading, error: raceError } = useRace(id);
  const { data: entriesData, isLoading: entriesLoading } = useRaceEntries(id);
  const { data: prediction, isLoading: predictionLoading } = usePrediction(id);
  const { data: simulation, isLoading: simulationLoading } = useSimulation(id);
  const createPrediction = useCreatePrediction();
  const fetchShutubaOdds = useFetchShutubaOdds();

  const handleFetchOdds = async () => {
    if (!netkeibaRaceId.trim()) return;
    try {
      const result = await fetchShutubaOdds.mutateAsync({
        raceId: id,
        netkeibaRaceId: netkeibaRaceId.trim(),
      });
      alert(`${result.message}\n更新: ${result.data?.updated || 0}頭`);
      setShowFetchForm(false);
      setNetkeibaRaceId('');
    } catch (error) {
      console.error('Fetch odds failed:', error);
      alert('オッズ取得に失敗しました');
    }
  };

  if (raceLoading || entriesLoading) {
    return <PageLoading />;
  }

  if (raceError || !race) {
    return <ErrorMessage message="レース情報の取得に失敗しました" />;
  }

  const formattedDate = new Date(race.date).toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  const handlePredict = async () => {
    try {
      await createPrediction.mutateAsync(id);
    } catch (error) {
      console.error('Prediction failed:', error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="text-sm">
        <Link to="/races" className="text-primary-600 hover:underline">
          レース一覧
        </Link>
        <span className="mx-2 text-gray-400">/</span>
        <span className="text-gray-600">{race.name}</span>
      </nav>

      {/* Race Header */}
      <div className="card">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <GradeBadge grade={race.grade} />
              <CourseTypeBadge type={race.course_type} />
              {race.track_condition && (
                <span className="text-sm text-gray-500">
                  馬場: {race.track_condition}
                </span>
              )}
            </div>
            <h1 className="text-2xl font-bold text-gray-900">{race.name}</h1>
            <p className="mt-1 text-gray-500">
              {formattedDate} / {race.venue} / {race.distance}m
            </p>
          </div>
          <button
            onClick={handlePredict}
            disabled={createPrediction.isPending || !entriesData?.items.length}
            className="btn btn-primary"
          >
            {createPrediction.isPending ? '予測中...' : '予測実行'}
          </button>
        </div>
      </div>

      {/* Prediction Result */}
      {predictionLoading ? (
        <div className="card text-center py-8 text-gray-500">
          予測結果を読み込み中...
        </div>
      ) : prediction ? (
        <div className="space-y-6">
          {/* Confidence */}
          <div className="card">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">予測結果</h2>
                <p className="text-sm text-gray-500">
                  {new Date(prediction.predicted_at).toLocaleString('ja-JP')} /
                  モデル {prediction.model_version}
                </p>
              </div>
              {prediction.confidence_score !== null && (
                <div className="text-right">
                  <div className="text-sm text-gray-500">信頼度</div>
                  <div className="text-2xl font-bold text-primary-600">
                    {(prediction.confidence_score * 100).toFixed(0)}%
                  </div>
                </div>
              )}
            </div>
            {prediction.reasoning && (
              <p className="mt-4 p-3 bg-gray-50 rounded-lg text-gray-700">
                {prediction.reasoning}
              </p>
            )}
          </div>

          {/* Rankings */}
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">予測ランキング</h2>
            <RankingTable rankings={prediction.rankings} />
          </div>

          {/* Pace & Bets */}
          <div className="grid gap-6 lg:grid-cols-2">
            {prediction.pace_prediction && (
              <PacePreview pace={prediction.pace_prediction} />
            )}
            {prediction.recommended_bets && (
              <BetRecommendation bets={prediction.recommended_bets} />
            )}
          </div>
        </div>
      ) : (
        <div className="card text-center py-8 text-gray-500">
          予測結果がありません。「予測実行」ボタンをクリックしてください。
        </div>
      )}

      {/* Race Simulation */}
      {simulationLoading ? (
        <div className="card text-center py-8 text-gray-500">
          シミュレーションデータを読み込み中...
        </div>
      ) : simulation ? (
        <div className="card">
          <RaceSimulationView simulation={simulation} />
        </div>
      ) : entriesData && entriesData.items.length > 0 ? (
        <div className="card text-center py-8 text-gray-500">
          シミュレーションデータの取得に失敗しました
        </div>
      ) : null}

      {/* Entry Table */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">
            出走馬一覧
            {entriesData && (
              <span className="ml-2 text-sm font-normal text-gray-500">
                ({entriesData.total}頭)
              </span>
            )}
          </h2>
          <button
            onClick={() => setShowFetchForm(!showFetchForm)}
            className="text-sm px-3 py-1.5 bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
          >
            netkeibaから更新
          </button>
        </div>

        {/* Netkeiba Fetch Form */}
        {showFetchForm && (
          <div className="mb-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
            <p className="text-sm text-gray-600 mb-2">
              netkeibaのレースIDを入力してオッズ・人気を一括更新します。
            </p>
            <p className="text-xs text-gray-500 mb-3">
              例: 有馬記念2024の場合 → <code className="bg-gray-200 px-1 rounded">202406050811</code>
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                value={netkeibaRaceId}
                onChange={(e) => setNetkeibaRaceId(e.target.value)}
                placeholder="netkeiba race ID (例: 202406050811)"
                className="flex-1 px-3 py-2 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
              />
              <button
                onClick={handleFetchOdds}
                disabled={fetchShutubaOdds.isPending || !netkeibaRaceId.trim()}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
              >
                {fetchShutubaOdds.isPending ? '取得中...' : '取得'}
              </button>
              <button
                onClick={() => {
                  setShowFetchForm(false);
                  setNetkeibaRaceId('');
                }}
                className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 text-sm"
              >
                閉じる
              </button>
            </div>
          </div>
        )}

        {entriesData && entriesData.items.length > 0 ? (
          <EntryTable entries={entriesData.items} />
        ) : (
          <p className="text-gray-500 text-center py-4">出走馬がありません</p>
        )}
      </div>
    </div>
  );
}
