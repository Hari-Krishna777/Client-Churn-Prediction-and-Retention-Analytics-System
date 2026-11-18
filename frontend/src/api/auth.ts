import { apiClient } from './client';
import { AuthResponse } from '../types';

export const authApi = {
  login: async (username: string, password: string): Promise<AuthResponse> => {
    const { data } = await apiClient.post<AuthResponse>('/auth/login', { username, password });
    return data;
  },

  register: async (username: string, email: string, password: string): Promise<AuthResponse> => {
    const { data } = await apiClient.post<AuthResponse>('/auth/register', { username, email, password });
    return data;
  },

  getCurrentUser: async (): Promise<AuthResponse> => {
    const { data } = await apiClient.get<AuthResponse>('/auth/me');
    return data;
  },
};
