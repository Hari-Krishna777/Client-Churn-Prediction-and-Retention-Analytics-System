import { apiClient } from './client';
import { RetentionAction, RetentionStats } from '../types';

export interface RetentionActionParams {
  status?: string;
  priority?: string;
  urgency?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface RetentionActionListResponse {
  total: number;
  limit: number;
  offset: number;
  actions: RetentionAction[];
}

export const retentionApi = {
  listActions: async (params: RetentionActionParams = {}): Promise<RetentionActionListResponse> => {
    const searchParams = new URLSearchParams();
    if (params.status) searchParams.append('status', params.status);
    if (params.priority) searchParams.append('priority', params.priority);
    if (params.urgency) searchParams.append('urgency', params.urgency);
    if (params.search) searchParams.append('search', params.search);
    if (params.limit) searchParams.append('limit', String(params.limit));
    if (params.offset !== undefined) searchParams.append('offset', String(params.offset));

    const { data } = await apiClient.get<RetentionActionListResponse>(`/retention/actions?${searchParams.toString()}`);
    return data;
  },

  updateStatus: async (
    recommendationId: string,
    status: string,
    notes?: string
  ): Promise<{ id: string; status: string; notes?: string; message: string }> => {
    const { data } = await apiClient.patch(`/retention/${encodeURIComponent(recommendationId)}/status`, {
      status,
      notes,
    });
    return data;
  },

  getStats: async (): Promise<RetentionStats> => {
    const { data } = await apiClient.get<RetentionStats>('/retention/stats');
    return data;
  },
};
