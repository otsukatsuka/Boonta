// Race hooks with React Query

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { racesApi } from '../api';
import type { RaceCreate, RaceUpdate } from '../types';

export const raceKeys = {
  all: ['races'] as const,
  lists: () => [...raceKeys.all, 'list'] as const,
  list: (params?: object) => [...raceKeys.lists(), params] as const,
  upcoming: (limit?: number) => [...raceKeys.all, 'upcoming', limit] as const,
  search: (name: string) => [...raceKeys.all, 'search', name] as const,
  details: () => [...raceKeys.all, 'detail'] as const,
  detail: (id: number) => [...raceKeys.details(), id] as const,
};

export function useRaces(params?: { skip?: number; limit?: number; grade?: string }) {
  return useQuery({
    queryKey: raceKeys.list(params),
    queryFn: () => racesApi.getAll(params),
  });
}

export function useUpcomingRaces(limit = 10) {
  return useQuery({
    queryKey: raceKeys.upcoming(limit),
    queryFn: () => racesApi.getUpcoming(limit),
  });
}

export function useSearchRaces(name: string, enabled = true) {
  return useQuery({
    queryKey: raceKeys.search(name),
    queryFn: () => racesApi.search(name),
    enabled: enabled && name.length > 0,
  });
}

export function useRace(raceId: number) {
  return useQuery({
    queryKey: raceKeys.detail(raceId),
    queryFn: () => racesApi.getById(raceId),
    enabled: raceId > 0,
  });
}

export function useCreateRace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: RaceCreate) => racesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: raceKeys.lists() });
    },
  });
}

export function useUpdateRace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ raceId, data }: { raceId: number; data: RaceUpdate }) =>
      racesApi.update(raceId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: raceKeys.detail(variables.raceId) });
      queryClient.invalidateQueries({ queryKey: raceKeys.lists() });
    },
  });
}

export function useDeleteRace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (raceId: number) => racesApi.delete(raceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: raceKeys.lists() });
    },
  });
}
