import type {
  BacktestRunRequest,
  BacktestRunResponse,
  PredictBatchResponse,
  PredictResponse,
  RaceDetail,
  RaceListItem,
  SensitivityRow,
  Strategy,
  SystemStatus,
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
  listStrategies: () => jget<Strategy[]>(`/api/backtest/strategies`),
  getSensitivity: (runId: number) =>
    jget<SensitivityRow[]>(`/api/backtest/${runId}/sensitivity`),
  runBacktest: (req: BacktestRunRequest) =>
    jpost<BacktestRunResponse>(`/api/backtest/run`, req),
};
