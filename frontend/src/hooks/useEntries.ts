// Entry hooks with React Query

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { entriesApi } from '../api';
import type { EntryCreate, EntryUpdate, WorkoutUpdate, CommentUpdate } from '../types';
import { raceKeys } from './useRaces';

export const entryKeys = {
  all: ['entries'] as const,
  byRace: (raceId: number) => [...entryKeys.all, 'race', raceId] as const,
};

export function useRaceEntries(raceId: number) {
  return useQuery({
    queryKey: entryKeys.byRace(raceId),
    queryFn: () => entriesApi.getByRace(raceId),
    enabled: raceId > 0,
  });
}

export function useCreateEntry() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ raceId, data }: { raceId: number; data: EntryCreate }) =>
      entriesApi.create(raceId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: entryKeys.byRace(variables.raceId) });
      queryClient.invalidateQueries({ queryKey: raceKeys.detail(variables.raceId) });
    },
  });
}

export function useUpdateEntry() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ entryId, data }: { entryId: number; data: EntryUpdate }) =>
      entriesApi.update(entryId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: entryKeys.all });
    },
  });
}

export function useUpdateWorkout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ entryId, data }: { entryId: number; data: WorkoutUpdate }) =>
      entriesApi.updateWorkout(entryId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: entryKeys.all });
    },
  });
}

export function useUpdateComment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ entryId, data }: { entryId: number; data: CommentUpdate }) =>
      entriesApi.updateComment(entryId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: entryKeys.all });
    },
  });
}
