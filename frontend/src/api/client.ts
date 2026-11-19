import axios, { AxiosError } from 'axios';

// Vite dev server proxies `/api` to `http://127.0.0.1:8000`
// Or if direct backend URL is configured via VITE_API_URL
const baseURL = import.meta.env.VITE_API_URL || '/api';

export const apiClient = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to attach authentication token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('churniq_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for consistent error messaging
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ detail?: string | string[] } | Blob>) => {
    let message = 'An unexpected network error occurred.';
    if (error.response?.data) {
      if (error.response.data instanceof Blob) {
        try {
          const text = await error.response.data.text();
          const parsed = JSON.parse(text);
          if (parsed.detail) {
            message = Array.isArray(parsed.detail) ? parsed.detail.join(', ') : parsed.detail;
          }
        } catch {
          message = error.message || message;
        }
      } else if (typeof error.response.data === 'object' && 'detail' in error.response.data && error.response.data.detail) {
        const detail = error.response.data.detail;
        message = Array.isArray(detail) ? detail.join(', ') : detail;
      }
    } else if (error.message) {
      message = error.message;
    }
    return Promise.reject(new Error(message));
  }
);
