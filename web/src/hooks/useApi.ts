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

export function useStrategies(dateFrom?: string, dateTo?: string) {
  return useQuery({
    queryKey: ["strategies", dateFrom ?? null, dateTo ?? null],
    queryFn: () => api.listStrategies(dateFrom, dateTo),
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

/* ---------- DATA tab ---------- */

export function useFeeds() {
  return useQuery({
    queryKey: ["feeds"],
    queryFn: () => api.getFeeds(),
    staleTime: 60_000,
  });
}

export function useCoverage(fromYear?: number, toYear?: number) {
  return useQuery({
    queryKey: ["coverage", fromYear ?? null, toYear ?? null],
    queryFn: () => api.getCoverage(fromYear, toYear),
    staleTime: 5 * 60_000,
  });
}

export function useFeatures() {
  return useQuery({
    queryKey: ["features"],
    queryFn: () => api.getFeatures(),
    staleTime: Infinity,
  });
}

export function useFeatureStats() {
  return useQuery({
    queryKey: ["featureStats"],
    queryFn: () => api.getFeatureStats(),
    staleTime: 5 * 60_000,
  });
}

/* ---------- MODEL tab ---------- */

export function useModelStatus() {
  return useQuery({
    queryKey: ["modelStatus"],
    queryFn: () => api.getModelStatus(),
    staleTime: 60_000,
  });
}

export function useTrainingRuns(limit = 6) {
  return useQuery({
    queryKey: ["trainingRuns", limit],
    queryFn: () => api.getTrainingRuns(limit),
    staleTime: 60_000,
  });
}

export function useLeaderboard(runId: string | undefined) {
  return useQuery({
    queryKey: ["leaderboard", runId ?? null],
    queryFn: () => api.getLeaderboard(runId),
    staleTime: 5 * 60_000,
  });
}

export function useFeatureImportance() {
  return useQuery({
    queryKey: ["featureImportance"],
    queryFn: () => api.getFeatureImportance(),
    staleTime: 5 * 60_000,
    retry: 1,
  });
}

export function useCalibration(runId: string | undefined) {
  return useQuery({
    queryKey: ["calibration", runId ?? null],
    queryFn: () => api.getCalibration(runId),
    staleTime: 5 * 60_000,
  });
}
