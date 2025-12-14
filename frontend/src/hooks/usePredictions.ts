// Prediction hooks with React Query

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { predictionsApi, modelApi } from '../api';

export const predictionKeys = {
  all: ['predictions'] as const,
  byRace: (raceId: number) => [...predictionKeys.all, 'race', raceId] as const,
  history: (raceId: number) => [...predictionKeys.byRace(raceId), 'history'] as const,
};

export const modelKeys = {
  all: ['model'] as const,
  status: () => [...modelKeys.all, 'status'] as const,
  featureImportance: () => [...modelKeys.all, 'feature-importance'] as const,
};

export function usePrediction(raceId: number) {
  return useQuery({
    queryKey: predictionKeys.byRace(raceId),
    queryFn: () => predictionsApi.getByRace(raceId),
    enabled: raceId > 0,
    retry: false, // Don't retry on 404
  });
}

export function usePredictionHistory(raceId: number, limit = 10) {
  return useQuery({
    queryKey: predictionKeys.history(raceId),
    queryFn: () => predictionsApi.getHistory(raceId, limit),
    enabled: raceId > 0,
  });
}

export function useCreatePrediction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (raceId: number) => predictionsApi.create(raceId),
    onSuccess: (_, raceId) => {
      queryClient.invalidateQueries({ queryKey: predictionKeys.byRace(raceId) });
      queryClient.invalidateQueries({ queryKey: predictionKeys.history(raceId) });
    },
  });
}

export function useModelStatus() {
  return useQuery({
    queryKey: modelKeys.status(),
    queryFn: () => modelApi.getStatus(),
  });
}

export function useFeatureImportance() {
  return useQuery({
    queryKey: modelKeys.featureImportance(),
    queryFn: () => modelApi.getFeatureImportance(),
  });
}
