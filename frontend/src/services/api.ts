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

// Request interceptor for authentication and logging
api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);

    // Add auth token to all requests
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

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

    // Redirect to login on 401
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }

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
  const skip = (page - 1) * pageSize;
  const params = new URLSearchParams({
    skip: skip.toString(),
    limit: pageSize.toString(),
  });

  if (sourceDbType) {
    params.append('database', sourceDbType);
  }

  const response = await api.get(`/api/v1/queries?${params.toString()}`);

  // Transform new API response to match old structure
  const data = response.data;
  const queries = (data.queries || []).map((q: any) => ({
    id: q.id?.toString() || '',
    fingerprint: q.sql_fingerprint || '',
    execution_count: 1, // New API doesn't aggregate, each row is one execution
    avg_duration_ms: Math.round((q.query_time || 0) * 1000),
    p95_duration_ms: Math.round((q.query_time || 0) * 1000),
    max_duration_ms: Math.round((q.query_time || 0) * 1000),
    min_duration_ms: Math.round((q.query_time || 0) * 1000),
    source_db_type: q.database_name || 'unknown',
    source_db_host: q.user_host || 'unknown',
    last_seen: q.start_time || q.collected_at || new Date().toISOString(),
    has_analysis: false,
    max_improvement_level: q.severity === 'HIGH' ? 'HIGH' : q.severity === 'MEDIUM' ? 'MEDIUM' : 'LOW'
  }));

  return {
    items: queries,
    total: data.total || 0,
    page: page,
    page_size: pageSize,
    total_pages: Math.ceil((data.total || 0) / pageSize)
  };
};

export const getSlowQueryDetail = async (id: string): Promise<SlowQueryDetail> => {
  const response = await api.get(`/api/v1/queries/${id}`);
  const q = response.data;

  // Transform new API response to match old structure
  return {
    id: q.id?.toString() || '',
    source_db_type: q.database_name || 'unknown',
    source_db_host: q.user_host || 'unknown',
    source_db_name: q.database_name || 'unknown',
    fingerprint: q.sql_fingerprint || '',
    full_sql: q.sql_text || '',
    sql_hash: q.sql_fingerprint || '',
    duration_ms: Math.round((q.query_time || 0) * 1000),
    rows_examined: q.rows_examined || 0,
    rows_returned: q.rows_sent || 0,
    plan_json: null,
    plan_text: null,
    captured_at: q.start_time || q.collected_at || new Date().toISOString(),
    status: 'NEW',
    analysis: undefined
  };
};

export const deleteSlowQuery = async (_id: string): Promise<void> => {
  // Delete endpoint not yet implemented in multi-tenant version
  console.warn('Delete query not implemented in multi-tenant version');
};

// ============================================================================
// Statistics
// ============================================================================

export const getStats = async (): Promise<StatsResponse> => {
  const response = await api.get('/api/v1/stats/dashboard');
  const data = response.data;

  // Transform new API response to match old structure
  return {
    total_slow_queries: data.slow_queries || 0,
    total_analyzed: 0, // Not available in new API
    total_pending: data.slow_queries || 0,
    databases_monitored: 1, // Simplified for now
    top_tables: [],
    improvement_summary: [],
    recent_trend: []
  };
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

// ============================================================================
// Collector Agents (new multi-tenant system)
// ============================================================================

export const listCollectorAgents = async (): Promise<{ collectors: any[], total: number }> => {
  const response = await api.get('/api/v1/collectors');
  return response.data;
};

export const getCollectorAgent = async (id: number): Promise<any> => {
  const response = await api.get(`/api/v1/collectors/${id}`);
  return response.data;
};

export const registerCollectorAgent = async (data: any): Promise<{ id: number; api_key: string; name: string; type: string }> => {
  const response = await api.post('/api/v1/collectors/register', data);
  return response.data;
};

export const updateCollectorAgent = async (id: number, data: any): Promise<any> => {
  const response = await api.patch(`/api/v1/collectors/${id}`, data);
  return response.data;
};

export const deleteCollectorAgent = async (id: number): Promise<void> => {
  await api.delete(`/api/v1/collectors/${id}`);
};

export const startCollectorAgent = async (id: number): Promise<void> => {
  await api.post(`/api/v1/collectors/${id}/start`);
};

export const stopCollectorAgent = async (id: number): Promise<void> => {
  await api.post(`/api/v1/collectors/${id}/stop`);
};

export const triggerCollectorAgentCollection = async (id: number): Promise<void> => {
  await api.post(`/api/v1/collectors/${id}/collect`);
};

export const getCollectorAgentCommands = async (id: number, limit: number = 50): Promise<any[]> => {
  const response = await api.get(`/api/v1/collectors/${id}/commands`, { params: { limit } });
  return response.data;
};

// ============================================================================
// Organizations
// ============================================================================

export const listOrganizations = async (): Promise<any[]> => {
  const response = await api.get('/api/v1/admin/organizations');
  return response.data;
};

export const getOrganization = async (id: number): Promise<any> => {
  const response = await api.get(`/api/v1/admin/organizations/${id}`);
  return response.data;
};

export const createOrganization = async (data: any): Promise<any> => {
  const response = await api.post('/api/v1/admin/organizations', data);
  return response.data;
};

export const regenerateOrgApiKey = async (id: number): Promise<{ api_key: string }> => {
  const response = await api.post(`/api/v1/admin/organizations/${id}/regenerate-api-key`);
  return response.data;
};

export const deleteOrganization = async (id: number): Promise<void> => {
  await api.delete(`/api/v1/admin/organizations/${id}`);
};

export default api;
