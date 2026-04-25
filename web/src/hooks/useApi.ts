import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

export function useSystemStatus() {
  return useQuery({
    queryKey: ["systemStatus"],
    queryFn: () => api.getSystemStatus(),
    staleTime: 60_000,
  });
}

export function useRaces(date: string) {
  return useQuery({
    queryKey: ["races", date],
    queryFn: () => api.listRaces(date),
    staleTime: 30_000,
  });
}

export function useRaceDetail(raceKey: string | undefined) {
  return useQuery({
    queryKey: ["raceDetail", raceKey],
    queryFn: () => api.getRace(raceKey!),
    enabled: !!raceKey,
    staleTime: 30_000,
  });
}

export function usePredictRace(raceKey: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.predictRace(raceKey!),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["raceDetail", res.race_key] });
      qc.invalidateQueries({ queryKey: ["races"] });
    },
  });
}

export function usePredictBatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (date: string) => api.predictBatch(date),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["races"] });
      qc.invalidateQueries({ queryKey: ["raceDetail"] });
    },
  });
}

export function useStrategies() {
  return useQuery({
    queryKey: ["strategies"],
    queryFn: () => api.listStrategies(),
    staleTime: 5 * 60_000,
  });
}

export function useSensitivity(runId: number | undefined) {
  return useQuery({
    queryKey: ["sensitivity", runId],
    queryFn: () => api.getSensitivity(runId!),
    enabled: !!runId,
    staleTime: 5 * 60_000,
  });
}

export function useRunBacktest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: Parameters<typeof api.runBacktest>[0]) => api.runBacktest(req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["strategies"] });
      qc.invalidateQueries({ queryKey: ["sensitivity"] });
    },
  });
}
