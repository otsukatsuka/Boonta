import type {
  BacktestRunRequest,
  BacktestRunResponse,
  CalibrationResponse,
  CoverageResponse,
  FeatureImportanceRow,
  FeatureMeta,
  FeatureStat,
  FeedsResponse,
  LeaderboardResponse,
  ModelStatusOut,
  PredictBatchResponse,
  PredictResponse,
  RaceDetail,
  RaceListItem,
  SensitivityRow,
  Strategy,
  SystemStatus,
  TrainingRunOut,
} from "./types";

const BASE = ""; // dev proxy & same-origin in prod

async function jget<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`GET ${path} → ${r.status}`);
  return r.json();
}

async function jpost<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    throw new Error(`POST ${path} → ${r.status} ${text}`);
  }
  return r.json();
}

export const api = {
  getSystemStatus: () => jget<SystemStatus>("/api/system/status"),
  listRaces: (date: string) => jget<RaceListItem[]>(`/api/races?date=${date}`),
  getRace: (raceKey: string) => jget<RaceDetail>(`/api/races/${raceKey}`),
  predictRace: (raceKey: string) =>
    jpost<PredictResponse>(`/api/races/${raceKey}/predict`),
  predictBatch: (date: string) =>
    jpost<PredictBatchResponse>(`/api/races/predict-batch`, { date }),
  listStrategies: (dateFrom?: string, dateTo?: string) => {
    const qs =
      dateFrom && dateTo
        ? `?date_from=${dateFrom}&date_to=${dateTo}`
        : "";
    return jget<Strategy[]>(`/api/backtest/strategies${qs}`);
  },
  getSensitivity: (runId: number) =>
    jget<SensitivityRow[]>(`/api/backtest/${runId}/sensitivity`),
  runBacktest: (req: BacktestRunRequest) =>
    jpost<BacktestRunResponse>(`/api/backtest/run`, req),

  getFeeds: () => jget<FeedsResponse>("/api/system/feeds"),
  getCoverage: (fromYear?: number, toYear?: number) => {
    const qs: string[] = [];
    if (fromYear) qs.push(`from_year=${fromYear}`);
    if (toYear) qs.push(`to_year=${toYear}`);
    const q = qs.length ? `?${qs.join("&")}` : "";
    return jget<CoverageResponse>(`/api/system/coverage${q}`);
  },
  getFeatures: () => jget<FeatureMeta[]>("/api/system/features"),
  getFeatureStats: () => jget<FeatureStat[]>("/api/system/feature-stats"),

  getModelStatus: () => jget<ModelStatusOut>("/api/model/status"),
  getTrainingRuns: (limit = 6) =>
    jget<TrainingRunOut[]>(`/api/model/training-runs?limit=${limit}`),
  getLeaderboard: (runId?: string) => {
    const q = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
    return jget<LeaderboardResponse>(`/api/model/leaderboard${q}`);
  },
  getFeatureImportance: () =>
    jget<FeatureImportanceRow[]>("/api/model/feature-importance"),
  getCalibration: (runId?: string) => {
    const q = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
    return jget<CalibrationResponse>(`/api/model/calibration${q}`);
  },
};
