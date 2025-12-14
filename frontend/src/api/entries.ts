// Entry API functions

import apiClient from './client';
import type {
  Entry,
  EntryCreate,
  EntryListResponse,
  EntryUpdate,
  WorkoutUpdate,
  CommentUpdate,
} from '../types';

export const entriesApi = {
  // Get all entries for a race
  getByRace: async (raceId: number): Promise<EntryListResponse> => {
    const response = await apiClient.get(`/races/${raceId}/entries`);
    return response.data;
  },

  // Add entry to race
  create: async (raceId: number, data: EntryCreate): Promise<Entry> => {
    const response = await apiClient.post(`/races/${raceId}/entries`, data);
    return response.data;
  },

  // Update entry
  update: async (entryId: number, data: EntryUpdate): Promise<Entry> => {
    const response = await apiClient.put(`/entries/${entryId}`, data);
    return response.data;
  },

  // Update workout info
  updateWorkout: async (entryId: number, data: WorkoutUpdate): Promise<Entry> => {
    const response = await apiClient.put(`/entries/${entryId}/workout`, data);
    return response.data;
  },

  // Update trainer comment
  updateComment: async (entryId: number, data: CommentUpdate): Promise<Entry> => {
    const response = await apiClient.put(`/entries/${entryId}/comment`, data);
    return response.data;
  },
};
