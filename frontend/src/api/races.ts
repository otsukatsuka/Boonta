// Race API functions

import apiClient from './client';
import type { Race, RaceCreate, RaceListResponse, RaceUpdate } from '../types';

export interface RegisterRaceRequest {
  netkeiba_race_id: string;
  fetch_odds?: boolean;
  fetch_running_styles?: boolean;
}

export interface RegisterRaceResponse {
  success: boolean;
  message: string;
  race_id: number | null;
  race_name: string | null;
  entries_count: number;
  odds_updated: number;
}

export const racesApi = {
  // Get all races with pagination
  getAll: async (params?: {
    skip?: number;
    limit?: number;
    grade?: string;
  }): Promise<RaceListResponse> => {
    const response = await apiClient.get('/races', { params });
    return response.data;
  },

  // Get upcoming races
  getUpcoming: async (limit = 10): Promise<Race[]> => {
    const response = await apiClient.get('/races/upcoming', {
      params: { limit },
    });
    return response.data;
  },

  // Search races by name
  search: async (name: string, limit = 20): Promise<Race[]> => {
    const response = await apiClient.get('/races/search', {
      params: { name, limit },
    });
    return response.data;
  },

  // Get races by date range
  getByDateRange: async (
    startDate: string,
    endDate: string,
    grade?: string
  ): Promise<Race[]> => {
    const response = await apiClient.get('/races/by-date', {
      params: {
        start_date: startDate,
        end_date: endDate,
        grade,
      },
    });
    return response.data;
  },

  // Get single race by ID
  getById: async (raceId: number): Promise<Race> => {
    const response = await apiClient.get(`/races/${raceId}`);
    return response.data;
  },

  // Create new race
  create: async (data: RaceCreate): Promise<Race> => {
    const response = await apiClient.post('/races', data);
    return response.data;
  },

  // Update race
  update: async (raceId: number, data: RaceUpdate): Promise<Race> => {
    const response = await apiClient.put(`/races/${raceId}`, data);
    return response.data;
  },

  // Delete race
  delete: async (raceId: number): Promise<void> => {
    await apiClient.delete(`/races/${raceId}`);
  },

  // Register race from netkeiba ID
  registerFromNetkeiba: async (data: RegisterRaceRequest): Promise<RegisterRaceResponse> => {
    const response = await apiClient.post('/fetch/register', data);
    return response.data;
  },
};
