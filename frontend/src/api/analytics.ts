import { apiClient } from './client';
import {
  AnalyticsOverview,
  RiskDistributionResponse,
  ChurnFactorsResponse,
  CustomerSegmentsResponse,
  RecommendationSummaryResponse,
} from '../types';

export const analyticsApi = {
  getOverview: async (jobId?: string): Promise<AnalyticsOverview> => {
    const url = jobId ? `/analytics/overview?job_id=${encodeURIComponent(jobId)}` : '/analytics/overview';
    const { data } = await apiClient.get<AnalyticsOverview>(url);
    return data;
  },

  getRiskDistribution: async (jobId?: string): Promise<RiskDistributionResponse> => {
    const url = jobId ? `/analytics/risk-distribution?job_id=${encodeURIComponent(jobId)}` : '/analytics/risk-distribution';
    const { data } = await apiClient.get<RiskDistributionResponse>(url);
    return data;
  },

  getChurnFactors: async (jobId?: string, topN = 6): Promise<ChurnFactorsResponse> => {
    const params = new URLSearchParams({ top_n: String(topN) });
    if (jobId) params.append('job_id', jobId);
    const { data } = await apiClient.get<ChurnFactorsResponse>(`/analytics/churn-factors?${params.toString()}`);
    return data;
  },

  getSegments: async (jobId?: string): Promise<CustomerSegmentsResponse> => {
    const url = jobId ? `/analytics/segments?job_id=${encodeURIComponent(jobId)}` : '/analytics/segments';
    const { data } = await apiClient.get<CustomerSegmentsResponse>(url);
    return data;
  },

  getRecommendationsSummary: async (jobId?: string): Promise<RecommendationSummaryResponse> => {
    const url = jobId ? `/analytics/recommendations?job_id=${encodeURIComponent(jobId)}` : '/analytics/recommendations';
    const { data } = await apiClient.get<RecommendationSummaryResponse>(url);
    return data;
  },
};
