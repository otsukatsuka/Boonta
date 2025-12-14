// Common types

export type RunningStyle = 'ESCAPE' | 'FRONT' | 'STALKER' | 'CLOSER' | 'VERSATILE';
export type CourseType = '芝' | 'ダート';
export type TrackCondition = '良' | '稍重' | '重' | '不良';
export type Grade = 'G1' | 'G2' | 'G3' | 'OP' | 'L';
export type WorkoutEvaluation = 'A' | 'B' | 'C' | 'D';

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

export interface ApiError {
  detail: string;
}

// Running style display helpers
export const RUNNING_STYLE_LABELS: Record<RunningStyle, string> = {
  ESCAPE: '逃げ',
  FRONT: '先行',
  STALKER: '差し',
  CLOSER: '追込',
  VERSATILE: '自在',
};

export const RUNNING_STYLE_COLORS: Record<RunningStyle, string> = {
  ESCAPE: '#ef4444',
  FRONT: '#f97316',
  STALKER: '#eab308',
  CLOSER: '#3b82f6',
  VERSATILE: '#8b5cf6',
};

export const GRADE_LABELS: Record<Grade, string> = {
  G1: 'G1',
  G2: 'G2',
  G3: 'G3',
  OP: 'オープン',
  L: 'リステッド',
};
