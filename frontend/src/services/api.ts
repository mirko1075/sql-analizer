import axios from 'axios';

const API_BASE = '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface SlowQuery {
  id: number;
  sql_fingerprint: string;
  sql_text: string;
  query_time: number;
  rows_examined: number;
  rows_sent: number;
  database_name: string;
  analyzed: boolean;
  status: 'pending' | 'analyzed' | 'archived' | 'resolved';
  detected_at: string;
  lock_time: number | null;
  analyzed_at?: string | null;
}

export interface Issue {
  type: string;
  severity: string;
  message: string;
}

export interface SuggestedIndex {
  table: string;
  column: string;
  statement: string;
}

export interface AnalysisResult {
  query_id: number;
  sql_text: string;
  query_time: number;
  rows_examined: number;
  issues: Issue[];
  suggested_indexes: SuggestedIndex[];
  priority: string;
  ai_analysis: string;
  analyzed_at: string;
  analysis_duration: number;
}

export interface QueryListResponse {
  queries: SlowQuery[];
  total: number;
  skip: number;
  limit: number;
  has_more: boolean;
}

export interface Stats {
  total_queries: number;
  analyzed_queries: number;
  pending_queries: number;
  average_query_time: number;
  slowest_query: {
    id: number;
    query_time: number;
    sql_text: string;
  } | null;
}

// API methods
export const getSlowQueries = (skip = 0, limit = 50, analyzed?: boolean, status?: string) => {
  const params: any = { skip, limit };
  if (analyzed !== undefined) params.analyzed = analyzed;
  if (status) params.status = status;
  return api.get<QueryListResponse>('/slow-queries', { params });
};

export const getSlowQuery = (queryId: number) => {
  return api.get<SlowQuery>(`/slow-queries/${queryId}`);
};

export const getStats = () => {
  return api.get<Stats>('/slow-queries/stats/summary');
};

export const analyzeQuery = (queryId: number) => {
  return api.post(`/analyze/${queryId}`);
};

export const getAnalysis = (queryId: number) => {
  return api.get<AnalysisResult>(`/analyze/${queryId}`);
};

export const triggerCollection = () => {
  return api.post('/analyze/collect');
};

export const updateQueryStatus = (queryId: number, status: string) => {
  return api.patch(`/slow-queries/${queryId}/status`, { status });
};

export const archiveQuery = (queryId: number) => {
  return api.post(`/slow-queries/${queryId}/archive`);
};

export const resolveQuery = (queryId: number) => {
  return api.post(`/slow-queries/${queryId}/resolve`);
};

export const analyzeWithAI = (queryId: number) => {
  return api.post(`/ai/analyze/${queryId}`);
};

export const getAIAnalysis = (queryId: number) => {
  return api.get(`/ai/analysis/${queryId}`);
};

export const getAIStatus = () => {
  return api.get('/ai/status');
};

export default api;
