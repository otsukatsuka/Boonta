/**
 * API response types — must match src/api/schemas/ exactly (snake_case).
 * If the backend grows beyond this, switch to openapi-typescript.
 */

export interface MlTop {
  horse_number: number;
  name: string;
  prob: number;
}

export interface Horse {
  horse_number: number;
  waku: number | null;
  name: string;
  jockey: string | null;
  jockey_index: number | null;
  weight_carried: number | null;
  running_style: number | null; // 1-4
  idm: number | null;
  mid_position: number | null;
  late3f_position: number | null;
  goal_position: number | null;
  goal_io: number | null;       // 1-5
  odds: number | null;
  fukusho_odds: number | null;
  popularity: number | null;
  gate_miss_rate: number | null;
  upset_index: number | null;
  prob: number | null;
  ev_tan: number | null;
  ev_fuku: number | null;
}

export interface RaceListItem {
  race_key: string;
  held_on: string;        // ISO date YYYY-MM-DD
  venue_code: string;
  venue: string;
  race_no: number;
  name: string | null;
  grade: string | null;
  surface: string | null;
  distance: number | null;
  condition: string | null;
  weather: string | null;
  post_time: string | null;
  head_count: number | null;
  pace: string | null;    // "H" | "M" | "S"
  best_ev_tan: number | null;
  best_ev_fuku: number | null;
  ml_top: MlTop | null;
  status: "OPEN" | "DONE" | "NO_PREDICTION";
  horses: Horse[];
}

export interface RaceDetail {
  race: RaceListItem;
  horses: Horse[];
  updated_at: string | null;
}

export interface PredictResponse {
  race_key: string;
  horses: Horse[];
  model_version: string;
  predicted_at: string;
  elapsed_ms: number;
}

export interface PredictBatchItem {
  race_key: string;
  status: "ok" | "error" | "skipped";
  error?: string | null;
}

export interface PredictBatchResponse {
  jobs: PredictBatchItem[];
  elapsed_ms: number;
}

export interface SystemStatus {
  jrdb_sync: string | null;
  modal_ready: boolean;
  model_name: string;
  model_version: string | null;
  feature_count: number;
  ev_threshold_default: number;
  preset: string;
}

export interface EquityPoint {
  month: string;        // "YYYY-MM"
  cum: number;
}

export interface Strategy {
  run_id: number;
  id: string;
  label: string;
  kind: "ML" | "EV";
  date_from: string;
  date_to: string;
  ev_threshold: number | null;
  model_version: string;
  races: number;
  bet_races: number;
  invested: number;
  returned: number;
  hits: number;
  roi: number;
  equity: EquityPoint[];
  computed_at: string;
}

export interface SensitivityRow {
  thr: number;
  bet_races: number | null;
  hits: number | null;
  roi: number | null;
}

export interface BacktestRunRequest {
  strategy: string;
  date_from: string;
  date_to: string;
  ev_threshold: number;
  sensitivity: boolean;
}

export interface BacktestRunResponse {
  runs: Strategy[];
  elapsed_ms: number;
}

/** UI-side helpers (computed in TS, not from API). */
export interface NagashiPlan {
  axis: number | null;
  partners: number[];
  combos: number[][]; // [axis, p1, p2] sorted asc
}

export interface BetPlan {
  tansho: number[];
  fukusho: number[];
  umaren_box: number[][]; // [a, b]
  sanrenpuku_box: number[][]; // [a, b, c]
  nagashi: NagashiPlan;
}
