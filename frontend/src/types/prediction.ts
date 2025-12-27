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

export interface TrifectaBet {
  type: string;
  first: number[];
  second: number[];
  third: number[];
  combinations: number;
  amount_per_ticket: number;
}

export interface TrioBet {
  type: string;
  horses: number[];
  combinations: number;
  amount_per_ticket: number;
}

export interface ExactaBet {
  type: string;
  first: number;
  second: number[];
  combinations: number;
  amount_per_ticket: number;
}

export interface WideBet {
  pairs: number[][];
  note: string;
  amount_per_ticket: number;
}

export interface HighRiskBet {
  bet_type: string;
  horses: number[];
  expected_return: number;
  risk_level: 'medium' | 'high' | 'very_high';
  reason: string;
  amount: number;
}

export interface BetRecommendation {
  trifecta: TrifectaBet | null;
  trio: TrioBet | null;
  exacta: ExactaBet | null;
  wide: WideBet | null;
  total_investment: number;
  note: string | null;
  high_risk_bets: HighRiskBet[] | null;
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

// Risk level labels and colors
export const RISK_LABELS: Record<HighRiskBet['risk_level'], string> = {
  medium: '中リスク',
  high: '高リスク',
  very_high: '超高リスク',
};

export const RISK_COLORS: Record<HighRiskBet['risk_level'], string> = {
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-orange-100 text-orange-800',
  very_high: 'bg-red-100 text-red-800',
};
