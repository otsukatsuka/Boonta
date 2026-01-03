// Simulation types for race visualization

import type { RunningStyle } from './common';

export interface HorsePosition {
  horse_number: number;
  horse_name: string;
  running_style: RunningStyle | null;
  position: number;
  distance_from_leader: number;
}

export interface CornerPositions {
  corner_name: string;
  horses: HorsePosition[];
}

export interface FormationHorse {
  horse_number: number;
  horse_name: string;
  running_style: RunningStyle | null;
}

export interface FormationRow {
  row_index: number;
  row_label: string;
  horses: FormationHorse[];
}

export interface StartFormation {
  rows: FormationRow[];
  total_horses: number;
}

export interface ScenarioRanking {
  rank: number;
  horse_number: number;
  horse_name: string;
  score: number;
}

export interface ScenarioKeyHorse {
  horse_number: number;
  horse_name: string;
  reason: string;
}

export interface ScenarioResult {
  pace_type: 'slow' | 'middle' | 'high';
  pace_label: string;
  probability: number;
  rankings: ScenarioRanking[];
  key_horses: ScenarioKeyHorse[];
  advantageous_styles: string[];
  description: string;
}

export interface TrackConditionResult {
  track_condition: '良' | '稍重' | '重' | '不良';
  front_advantage: number;
  rankings: ScenarioRanking[];
  key_horses: ScenarioKeyHorse[];
  advantageous_styles: string[];
  description: string;
}

export interface AnimationHorse {
  horse_number: number;
  horse_name: string;
  running_style: RunningStyle | null;
  progress: number;
  lane: number;
}

export interface AnimationFrame {
  time: number;
  horses: AnimationHorse[];
}

export interface RaceSimulation {
  race_id: number;
  race_name: string;
  distance: number;
  course_type: string;
  venue: string | null;
  track_condition: string | null;
  venue_description: string | null;
  corner_positions: CornerPositions[];
  start_formation: StartFormation;
  scenarios: ScenarioResult[];
  track_condition_scenarios: TrackConditionResult[];
  predicted_pace: 'slow' | 'middle' | 'high';
  animation_frames: AnimationFrame[] | null;
}

// Corner labels in Japanese
export const CORNER_LABELS: Record<string, string> = {
  '1C': '1コーナー',
  '2C': '2コーナー',
  '3C': '3コーナー',
  '4C': '4コーナー',
  'goal': 'ゴール',
};
