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

  forgotPassword: async (email: string): Promise<{ message: string }> => {
    const { data } = await apiClient.post<{ message: string }>('/auth/forgot-password', { email });
    return data;
  },

  verifyResetToken: async (token: string): Promise<{ valid: boolean; email?: string; message?: string }> => {
    const { data } = await apiClient.get<{ valid: boolean; email?: string; message?: string }>(
      `/auth/verify-reset-token?token=${encodeURIComponent(token)}`
    );
    return data;
  },

  resetPassword: async (token: string, newPassword: string): Promise<{ message: string }> => {
    const { data } = await apiClient.post<{ message: string }>('/auth/reset-password', {
      token,
      new_password: newPassword,
    });
    return data;
  },
};
