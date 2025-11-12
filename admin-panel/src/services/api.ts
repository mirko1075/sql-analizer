import axios from 'axios';

// In production (Docker), nginx will proxy /api/ to api-gateway:8000
// In development, use Vite proxy or set VITE_API_BASE_URL to point to API Gateway
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  console.log('[API Interceptor] Request to:', config.url, 'Token:', token ? token.substring(0, 20) + '...' : 'NO TOKEN');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
    console.log('[API Interceptor] Authorization header added');
  } else {
    console.warn('[API Interceptor] No token found in localStorage');
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// API functions
export const authAPI = {
  login: (email: string, password: string) =>
    api.post('/api/v1/auth/login', { email, password }),
  logout: () => api.post('/api/v1/auth/logout'),
  getCurrentUser: () => api.get('/api/v1/auth/me'),
};

export const organizationsAPI = {
  list: () => api.get('/api/v1/admin/organizations'),
  get: (id: number) => api.get(`/api/v1/admin/organizations/${id}`),
  create: (data: any) => api.post('/api/v1/admin/organizations', data),
  update: (id: number, data: any) => api.put(`/api/v1/admin/organizations/${id}`, data),
  delete: (id: number) => api.delete(`/api/v1/admin/organizations/${id}`),
};

export const teamsAPI = {
  list: (orgId?: number) => api.get('/api/v1/admin/teams', { params: { organization_id: orgId } }),
  create: (data: any) => api.post('/api/v1/admin/teams', data),
};

export const usersAPI = {
  list: (orgId?: number) => api.get('/api/v1/admin/users', { params: { organization_id: orgId } }),
  create: (data: any) => api.post('/api/v1/admin/users', data),
};

export const queriesAPI = {
  list: (params?: any) => api.get('/api/v1/slow-queries', { params }),
  get: (id: number) => api.get(`/api/v1/slow-queries/${id}`),
  analyze: (id: number) => api.post(`/analyzer/analyze`, { slow_query_id: id }),
};

export const statsAPI = {
  dashboard: () => api.get('/api/v1/stats/dashboard'),
  rateLimit: () => api.get('/rate-limit/info'),
};
