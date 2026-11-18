import { apiClient } from './client';
import { CustomerListItem, CustomerDetailsResponse } from '../types';

export interface CustomerFilterParams {
  search?: string;
  dataset_id?: string;
  contract?: string;
  internet_service?: string;
  risk_category?: string;
  sort_by?: string;
  limit?: number;
  offset?: number;
}

export interface CustomerListResponse {
  total: number;
  limit: number;
  offset: number;
  customers: CustomerListItem[];
}

export const customersApi = {
  listCustomers: async (params: CustomerFilterParams = {}): Promise<CustomerListResponse> => {
    const searchParams = new URLSearchParams();
    if (params.search) searchParams.append('search', params.search);
    if (params.dataset_id) searchParams.append('dataset_id', params.dataset_id);
    if (params.contract) searchParams.append('contract', params.contract);
    if (params.internet_service) searchParams.append('internet_service', params.internet_service);
    if (params.risk_category) searchParams.append('risk_category', params.risk_category);
    if (params.sort_by) searchParams.append('sort_by', params.sort_by);
    if (params.limit) searchParams.append('limit', String(params.limit));
    if (params.offset !== undefined) searchParams.append('offset', String(params.offset));

    const { data } = await apiClient.get<CustomerListResponse>(`/customers?${searchParams.toString()}`);
    return data;
  },

  getCustomerDetails: async (customerId: string): Promise<CustomerDetailsResponse> => {
    const { data } = await apiClient.get<CustomerDetailsResponse>(`/customers/${encodeURIComponent(customerId)}`);
    return data;
  },
};
