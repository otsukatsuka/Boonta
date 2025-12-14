// Horse API functions

import apiClient from './client';
import type {
  Horse,
  HorseCreate,
  HorseListResponse,
  HorseUpdate,
  Jockey,
  JockeyCreate,
  JockeyListResponse,
  ResultListResponse,
} from '../types';

export const horsesApi = {
  // Get all horses with pagination
  getAll: async (params?: {
    skip?: number;
    limit?: number;
  }): Promise<HorseListResponse> => {
    const response = await apiClient.get('/horses', { params });
    return response.data;
  },

  // Search horses by name
  search: async (name: string, limit = 20): Promise<Horse[]> => {
    const response = await apiClient.get('/horses/search', {
      params: { name, limit },
    });
    return response.data;
  },

  // Get single horse by ID
  getById: async (horseId: number): Promise<Horse> => {
    const response = await apiClient.get(`/horses/${horseId}`);
    return response.data;
  },

  // Get horse race results
  getResults: async (horseId: number, limit = 10): Promise<ResultListResponse> => {
    const response = await apiClient.get(`/horses/${horseId}/results`, {
      params: { limit },
    });
    return response.data;
  },

  // Create new horse
  create: async (data: HorseCreate): Promise<Horse> => {
    const response = await apiClient.post('/horses', data);
    return response.data;
  },

  // Update horse
  update: async (horseId: number, data: HorseUpdate): Promise<Horse> => {
    const response = await apiClient.put(`/horses/${horseId}`, data);
    return response.data;
  },
};

export const jockeysApi = {
  // Get all jockeys with pagination
  getAll: async (params?: {
    skip?: number;
    limit?: number;
  }): Promise<JockeyListResponse> => {
    const response = await apiClient.get('/jockeys', { params });
    return response.data;
  },

  // Search jockeys by name
  search: async (name: string, limit = 20): Promise<Jockey[]> => {
    const response = await apiClient.get('/jockeys/search', {
      params: { name, limit },
    });
    return response.data;
  },

  // Get single jockey by ID
  getById: async (jockeyId: number): Promise<Jockey> => {
    const response = await apiClient.get(`/jockeys/${jockeyId}`);
    return response.data;
  },

  // Create new jockey
  create: async (data: JockeyCreate): Promise<Jockey> => {
    const response = await apiClient.post('/jockeys', data);
    return response.data;
  },
};
