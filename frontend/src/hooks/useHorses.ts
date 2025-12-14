// Horse hooks with React Query

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { horsesApi, jockeysApi } from '../api';
import type { HorseCreate, HorseUpdate, JockeyCreate } from '../types';

export const horseKeys = {
  all: ['horses'] as const,
  lists: () => [...horseKeys.all, 'list'] as const,
  list: (params?: object) => [...horseKeys.lists(), params] as const,
  search: (name: string) => [...horseKeys.all, 'search', name] as const,
  details: () => [...horseKeys.all, 'detail'] as const,
  detail: (id: number) => [...horseKeys.details(), id] as const,
  results: (id: number) => [...horseKeys.detail(id), 'results'] as const,
};

export const jockeyKeys = {
  all: ['jockeys'] as const,
  lists: () => [...jockeyKeys.all, 'list'] as const,
  list: (params?: object) => [...jockeyKeys.lists(), params] as const,
  search: (name: string) => [...jockeyKeys.all, 'search', name] as const,
  details: () => [...jockeyKeys.all, 'detail'] as const,
  detail: (id: number) => [...jockeyKeys.details(), id] as const,
};

// Horse hooks
export function useHorses(params?: { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: horseKeys.list(params),
    queryFn: () => horsesApi.getAll(params),
  });
}

export function useSearchHorses(name: string, enabled = true) {
  return useQuery({
    queryKey: horseKeys.search(name),
    queryFn: () => horsesApi.search(name),
    enabled: enabled && name.length > 0,
  });
}

export function useHorse(horseId: number) {
  return useQuery({
    queryKey: horseKeys.detail(horseId),
    queryFn: () => horsesApi.getById(horseId),
    enabled: horseId > 0,
  });
}

export function useHorseResults(horseId: number, limit = 10) {
  return useQuery({
    queryKey: horseKeys.results(horseId),
    queryFn: () => horsesApi.getResults(horseId, limit),
    enabled: horseId > 0,
  });
}

export function useCreateHorse() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: HorseCreate) => horsesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: horseKeys.lists() });
    },
  });
}

export function useUpdateHorse() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ horseId, data }: { horseId: number; data: HorseUpdate }) =>
      horsesApi.update(horseId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: horseKeys.detail(variables.horseId) });
    },
  });
}

// Jockey hooks
export function useJockeys(params?: { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: jockeyKeys.list(params),
    queryFn: () => jockeysApi.getAll(params),
  });
}

export function useSearchJockeys(name: string, enabled = true) {
  return useQuery({
    queryKey: jockeyKeys.search(name),
    queryFn: () => jockeysApi.search(name),
    enabled: enabled && name.length > 0,
  });
}

export function useJockey(jockeyId: number) {
  return useQuery({
    queryKey: jockeyKeys.detail(jockeyId),
    queryFn: () => jockeysApi.getById(jockeyId),
    enabled: jockeyId > 0,
  });
}

export function useCreateJockey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: JockeyCreate) => jockeysApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jockeyKeys.lists() });
    },
  });
}
