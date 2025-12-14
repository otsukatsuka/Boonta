import { useParams, Link } from 'react-router-dom';
import { useRace, useRaceEntries, usePrediction, useCreatePrediction } from '../hooks';
import { PageLoading, ErrorMessage, GradeBadge, CourseTypeBadge } from '../components/common';
import { EntryTable } from '../components/race';
import { RankingTable, PacePreview, BetRecommendation } from '../components/prediction';

export function RaceDetail() {
  const { raceId } = useParams<{ raceId: string }>();
  const id = parseInt(raceId || '0', 10);

  const { data: race, isLoading: raceLoading, error: raceError } = useRace(id);
  const { data: entriesData, isLoading: entriesLoading } = useRaceEntries(id);
  const { data: prediction, isLoading: predictionLoading } = usePrediction(id);
  const createPrediction = useCreatePrediction();

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

      {/* Entry Table */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">
          出走馬一覧
          {entriesData && (
            <span className="ml-2 text-sm font-normal text-gray-500">
              ({entriesData.total}頭)
            </span>
          )}
        </h2>
        {entriesData && entriesData.items.length > 0 ? (
          <EntryTable entries={entriesData.items} />
        ) : (
          <p className="text-gray-500 text-center py-4">出走馬がありません</p>
        )}
      </div>
    </div>
  );
}
