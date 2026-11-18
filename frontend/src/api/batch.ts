import { apiClient } from './client';
import { BatchPredictResponse, BatchJobItem } from '../types';

export const batchApi = {
  uploadCsv: async (file: File): Promise<BatchPredictResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await apiClient.post<BatchPredictResponse>('/batch/predict', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return data;
  },

  getJobStatus: async (jobId: string) => {
    const { data } = await apiClient.get(`/batch/${encodeURIComponent(jobId)}`);
    return data;
  },

  getJobResults: async (jobId: string, limit = 50, offset = 0) => {
    const { data } = await apiClient.get(`/batch/${encodeURIComponent(jobId)}/results?limit=${limit}&offset=${offset}`);
    return data;
  },

  listJobs: async (limit = 50, offset = 0): Promise<BatchJobItem[]> => {
    const { data } = await apiClient.get<BatchJobItem[]>(`/batch/jobs?limit=${limit}&offset=${offset}`);
    return data;
  },

  getDownloadUrl: (jobId: string): string => {
    const base = import.meta.env.VITE_API_URL || '/api';
    return `${base}/batch/${encodeURIComponent(jobId)}/download`;
  },
};
