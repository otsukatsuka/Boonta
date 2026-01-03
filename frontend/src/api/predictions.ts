// Prediction API functions

import apiClient from './client';
import type {
  PredictionResponse,
  PredictionHistoryListResponse,
  ModelStatus,
  FeatureImportance,
} from '../types';
import type { RaceSimulation } from '../types/simulation';

export const predictionsApi = {
  // Create new prediction for a race
  create: async (raceId: number): Promise<PredictionResponse> => {
    const response = await apiClient.post(`/predictions/${raceId}`);
    return response.data;
  },

  // Get latest prediction for a race
  getByRace: async (raceId: number): Promise<PredictionResponse> => {
    const response = await apiClient.get(`/predictions/${raceId}`);
    return response.data;
  },

  // Get prediction history for a race
  getHistory: async (
    raceId: number,
    limit = 10
  ): Promise<PredictionHistoryListResponse> => {
    const response = await apiClient.get(`/predictions/${raceId}/history`, {
      params: { limit },
    });
    return response.data;
  },

  // Get race simulation for visualization
  getSimulation: async (raceId: number): Promise<RaceSimulation> => {
    const response = await apiClient.get(`/predictions/${raceId}/simulation`);
    return response.data;
  },
};

export interface CollectTrainingDataRequest {
  netkeiba_race_id: string;
}

export interface CollectTrainingDataResponse {
  success: boolean;
  message: string;
  race_name: string | null;
  records_added: number;
  total_records: number;
}

export const modelApi = {
  // Get model status
  getStatus: async (): Promise<ModelStatus> => {
    const response = await apiClient.get('/model/status');
    return response.data;
  },

  // Get feature importance
  getFeatureImportance: async (): Promise<FeatureImportance> => {
    const response = await apiClient.get('/model/feature-importance');
    return response.data;
  },

  // Train model (returns 501 for now)
  train: async (): Promise<void> => {
    await apiClient.post('/model/train');
  },

  // Collect training data from a finished race
  collectTrainingData: async (
    data: CollectTrainingDataRequest
  ): Promise<CollectTrainingDataResponse> => {
    const response = await apiClient.post('/model/collect-training-data', data);
    return response.data;
  },
};
