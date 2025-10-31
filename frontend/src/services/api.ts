/**
 * API service for communicating with the FastAPI backend
 */
import axios from 'axios';
import type {
  SlowQuery,
  SlowQueryDetail,
  StatsResponse,
  CollectorStatus,
  AnalyzerStatus,
  HealthStatus,
  PaginatedResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API Error]', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ============================================================================
// Health & Status
// ============================================================================

export const getHealth = async (): Promise<HealthStatus> => {
  const response = await api.get('/health');
  return response.data;
};

// ============================================================================
// Slow Queries
// ============================================================================

export const getSlowQueries = async (
  page: number = 1,
  pageSize: number = 50,
  sourceDbType?: string
): Promise<PaginatedResponse<SlowQuery>> => {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
  });

  if (sourceDbType) {
    params.append('source_db_type', sourceDbType);
  }

  const response = await api.get(`/api/v1/slow-queries?${params.toString()}`);
  return response.data;
};

export const getSlowQueryDetail = async (id: string): Promise<SlowQueryDetail> => {
  const response = await api.get(`/api/v1/slow-queries/${id}`);
  return response.data;
};

export const deleteSlowQuery = async (id: string): Promise<void> => {
  await api.delete(`/api/v1/slow-queries/${id}`);
};

// ============================================================================
// Statistics
// ============================================================================

export const getStats = async (): Promise<StatsResponse> => {
  const response = await api.get('/api/v1/stats');
  return response.data;
};

export const getTopSlowQueries = async (
  limit: number = 10,
  minDurationMs?: number
): Promise<SlowQuery[]> => {
  const params = new URLSearchParams({
    limit: limit.toString(),
  });

  if (minDurationMs) {
    params.append('min_duration_ms', minDurationMs.toString());
  }

  const response = await api.get(`/api/v1/stats/top-slow-queries?${params.toString()}`);
  return response.data.queries;
};

export const getUnanalyzedQueries = async (limit: number = 10): Promise<SlowQuery[]> => {
  const params = new URLSearchParams({
    limit: limit.toString(),
  });

  const response = await api.get(`/api/v1/stats/unanalyzed-queries?${params.toString()}`);
  return response.data.queries;
};

export const getQueryTrends = async (days: number = 7): Promise<any> => {
  const params = new URLSearchParams({
    days: days.toString(),
  });

  const response = await api.get(`/api/v1/stats/trends?${params.toString()}`);
  return response.data;
};

// ============================================================================
// Collectors
// ============================================================================

export const getCollectorStatus = async (): Promise<CollectorStatus> => {
  const response = await api.get('/api/v1/collectors/status');
  return response.data;
};

export const triggerMySQLCollection = async (): Promise<void> => {
  await api.post('/api/v1/collectors/mysql/collect');
};

export const triggerPostgreSQLCollection = async (minDurationMs: number = 500): Promise<void> => {
  await api.post(`/api/v1/collectors/postgres/collect?min_duration_ms=${minDurationMs}`);
};

export const startScheduler = async (intervalMinutes: number = 5): Promise<void> => {
  await api.post(`/api/v1/collectors/scheduler/start?interval_minutes=${intervalMinutes}`);
};

export const stopScheduler = async (): Promise<void> => {
  await api.post('/api/v1/collectors/scheduler/stop');
};

// ============================================================================
// Analyzer
// ============================================================================

export const getAnalyzerStatus = async (): Promise<AnalyzerStatus> => {
  const response = await api.get('/api/v1/analyzer/status');
  return response.data;
};

export const triggerAnalysis = async (limit: number = 50): Promise<void> => {
  await api.post(`/api/v1/analyzer/analyze?limit=${limit}`);
};

export const analyzeSpecificQuery = async (queryId: string): Promise<void> => {
  await api.post(`/api/v1/analyzer/analyze/${queryId}`);
};

export default api;
