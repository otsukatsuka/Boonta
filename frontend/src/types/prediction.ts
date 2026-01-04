// Prediction types

export interface HorsePrediction {
  rank: number;
  horse_id: number;
  horse_name: string;
  horse_number: number;
  score: number;
  win_probability: number;
  place_probability: number;
  popularity: number | null;
  odds: number | null;
  is_dark_horse: boolean;
  dark_horse_reason: string | null;
}

export interface PacePrediction {
  type: 'slow' | 'middle' | 'high';
  confidence: number;
  reason: string;
  advantageous_styles: string[];
  escape_count: number;
  front_count: number;
}

// 三連複（新形式: 軸2頭流し）
export interface TrioBetNew {
  type: 'pivot_2_nagashi';
  pivots: number[];
  others: number[];
  combinations: number;
  amount_per_ticket: number;
}

// 三連複（旧形式: ボックス）
export interface TrioBetOld {
  type: string;
  horses: number[];
  combinations: number;
  amount_per_ticket: number;
}

// 三連単2頭軸マルチ（新形式）
export interface TrifectaMultiBet {
  type: 'pivot_2_multi';
  pivots: number[];
  others: number[];
  combinations: number;
  amount_per_ticket: number;
}

// 両形式に対応
export interface BetRecommendation {
  // 新形式
  trio?: TrioBetNew | TrioBetOld | null;
  trifecta_multi?: TrifectaMultiBet | null;
  // 旧形式（後方互換性）
  trifecta?: any;
  exacta?: any;
  wide?: any;
  high_risk_bets?: any[];
  // 共通
  total_investment: number;
  note: string | null;
}

export interface PredictionResponse {
  race_id: number;
  model_version: string;
  predicted_at: string;
  rankings: HorsePrediction[];
  pace_prediction: PacePrediction | null;
  recommended_bets: BetRecommendation | null;
  confidence_score: number | null;
  reasoning: string | null;
}

export interface PredictionHistory {
  id: number;
  race_id: number;
  model_version: string;
  predicted_at: string;
  confidence_score: number | null;
  created_at: string;
  updated_at: string;
}

export interface PredictionHistoryListResponse {
  items: PredictionHistory[];
  total: number;
}

export interface ModelStatus {
  model_version: string;
  is_trained: boolean;
  last_trained_at: string | null;
  training_data_count: number;
  metrics: Record<string, number> | null;
}

export interface FeatureImportance {
  features: Array<{
    name: string;
    importance: number;
  }>;
}

// Pace type labels
export const PACE_LABELS: Record<PacePrediction['type'], string> = {
  slow: 'スロー',
  middle: 'ミドル',
  high: 'ハイ',
};

export const PACE_COLORS: Record<PacePrediction['type'], string> = {
  slow: '#22c55e',
  middle: '#eab308',
  high: '#ef4444',
};
