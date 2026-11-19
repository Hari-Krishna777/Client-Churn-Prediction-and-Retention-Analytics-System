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
    const token = localStorage.getItem('churniq_token');
    const param = token ? `?token=${encodeURIComponent(token)}` : '';
    return `${base}/batch/${encodeURIComponent(jobId)}/download${param}`;
  },

  downloadCsv: async (jobId: string, filename?: string): Promise<void> => {
    const response = await apiClient.get(`/batch/${encodeURIComponent(jobId)}/download`, {
      responseType: 'blob',
    });

    let downloadFilename = filename
      ? `churn_predictions_${filename.replace(/\.csv$/i, '')}.csv`
      : `churn_predictions_${jobId}.csv`;

    const contentDisposition = response.headers?.['content-disposition'];
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="?([^";]+)"?/);
      if (match && match[1]) {
        downloadFilename = match[1];
      }
    }

    const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', downloadFilename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },
};
