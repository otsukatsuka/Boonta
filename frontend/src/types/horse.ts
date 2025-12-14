// Horse and Jockey types

export interface Horse {
  id: number;
  name: string;
  age: number | null;
  sex: string | null;
  trainer: string | null;
  owner: string | null;
  created_at: string;
  updated_at: string;
}

export interface HorseCreate {
  name: string;
  age?: number;
  sex?: string;
  trainer?: string;
  owner?: string;
}

export interface HorseUpdate {
  name?: string;
  age?: number;
  sex?: string;
  trainer?: string;
  owner?: string;
}

export interface HorseListResponse {
  items: Horse[];
  total: number;
}

export interface Jockey {
  id: number;
  name: string;
  win_rate: number | null;
  place_rate: number | null;
  venue_win_rate: number | null;
  created_at: string;
  updated_at: string;
}

export interface JockeyCreate {
  name: string;
  win_rate?: number;
  place_rate?: number;
  venue_win_rate?: number;
}

export interface JockeyListResponse {
  items: Jockey[];
  total: number;
}

export interface RaceResult {
  id: number;
  race_id: number;
  horse_id: number;
  jockey_id: number | null;
  position: number | null;
  time: number | null;
  margin: string | null;
  last_3f: number | null;
  corner_positions: Record<string, number> | null;
  prize: number | null;
  created_at: string;
  updated_at: string;
  horse_name: string | null;
  jockey_name: string | null;
  race_name: string | null;
}

export interface ResultListResponse {
  items: RaceResult[];
  total: number;
}
