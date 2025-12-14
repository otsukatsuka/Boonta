// Race types

import type { CourseType, Grade, TrackCondition } from './common';

export interface Race {
  id: number;
  name: string;
  date: string;
  venue: string;
  course_type: CourseType;
  distance: number;
  track_condition: TrackCondition | null;
  weather: string | null;
  grade: Grade;
  purse: number | null;
  entries_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface RaceCreate {
  name: string;
  date: string;
  venue: string;
  course_type: CourseType;
  distance: number;
  track_condition?: TrackCondition;
  weather?: string;
  grade: Grade;
  purse?: number;
}

export interface RaceUpdate {
  name?: string;
  date?: string;
  venue?: string;
  course_type?: CourseType;
  distance?: number;
  track_condition?: TrackCondition;
  weather?: string;
  grade?: Grade;
  purse?: number;
}

export interface RaceListResponse {
  items: Race[];
  total: number;
}

// Venue list
export const VENUES = [
  '東京',
  '中山',
  '阪神',
  '京都',
  '中京',
  '新潟',
  '福島',
  '小倉',
  '札幌',
  '函館',
] as const;
