// Race entry types

import type { RunningStyle, WorkoutEvaluation } from './common';

export interface Entry {
  id: number;
  race_id: number;
  horse_id: number;
  jockey_id: number | null;
  post_position: number | null;
  horse_number: number | null;
  weight: number | null;
  horse_weight: number | null;
  horse_weight_diff: number | null;
  odds: number | null;
  popularity: number | null;
  running_style: RunningStyle | null;
  trainer_comment: string | null;
  workout_time: string | null;
  workout_evaluation: WorkoutEvaluation | null;
  workout_course: string | null;
  workout_memo: string | null;
  created_at: string;
  updated_at: string;
  horse_name: string | null;
  jockey_name: string | null;
}

export interface EntryCreate {
  race_id: number;
  horse_id: number;
  jockey_id?: number;
  post_position?: number;
  horse_number?: number;
  weight?: number;
  horse_weight?: number;
  horse_weight_diff?: number;
  odds?: number;
  popularity?: number;
  running_style?: RunningStyle;
}

export interface EntryUpdate {
  jockey_id?: number;
  post_position?: number;
  horse_number?: number;
  weight?: number;
  horse_weight?: number;
  horse_weight_diff?: number;
  odds?: number;
  popularity?: number;
  running_style?: RunningStyle;
}

export interface WorkoutUpdate {
  workout_time?: string;
  workout_evaluation?: WorkoutEvaluation;
  workout_course?: string;
  workout_memo?: string;
}

export interface CommentUpdate {
  trainer_comment?: string;
}

export interface EntryListResponse {
  items: Entry[];
  total: number;
}
