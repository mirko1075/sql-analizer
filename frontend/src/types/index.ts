/**
 * Type definitions for AI Query Analyzer frontend
 */

export interface SlowQuery {
  id: string;
  fingerprint: string;
  execution_count: number;
  avg_duration_ms: number;
  p95_duration_ms: number;
  p99_duration_ms: number;
  max_duration_ms: number;
  min_duration_ms: number;
  source_db_type: string;
  source_db_host: string;
  first_seen: string;
  last_seen: string;
  has_analysis: boolean;
  improvement_level?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}

export interface SlowQueryDetail {
  id: string;
  source_db_type: string;
  source_db_host: string;
  source_db_name: string;
  fingerprint: string;
  full_sql: string;
  sql_hash: string;
  duration_ms: number;
  rows_examined: number;
  rows_returned: number;
  plan_json: any;
  plan_text: string | null;
  captured_at: string;
  status: 'NEW' | 'ANALYZED' | 'ERROR';
  analysis?: AnalysisResult;
}

export interface AnalysisResult {
  id: string;
  slow_query_id: string;
  problem: string;
  root_cause: string;
  suggestions: Suggestion[];
  improvement_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  estimated_speedup: string;
  analyzer_version: string;
  analysis_method: 'rule_based' | 'ai_assisted' | 'hybrid';
  confidence_score: number;
  analyzed_at: string;
  created_at: string;
}

export interface Suggestion {
  type: 'INDEX' | 'OPTIMIZATION' | 'REVIEW' | 'BEST_PRACTICE' | 'MONITORING';
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  description: string;
  sql?: string;
  estimated_impact?: string;
  rationale?: string;
}

export interface StatsResponse {
  total_queries: number;
  databases: {
    [key: string]: {
      count: number;
      avg_duration_ms: number;
    };
  };
  improvement_distribution: {
    [key: string]: number;
  };
  analysis_status: {
    analyzed: number;
    pending: number;
    error: number;
  };
  recent_activity: {
    last_24h: number;
    last_7d: number;
    last_30d: number;
  };
}

export interface CollectorStatus {
  is_running: boolean;
  jobs: Array<{
    id: string;
    name: string;
    next_run: string | null;
  }>;
  mysql_last_run: string | null;
  postgres_last_run: string | null;
  analyzer_last_run: string | null;
  mysql_total_collected: number;
  postgres_total_collected: number;
  total_analyzed: number;
}

export interface AnalyzerStatus {
  queries: {
    pending: number;
    analyzed: number;
    error: number;
    total: number;
  };
  analyses: {
    total: number;
    high_impact: number;
    medium_impact: number;
    low_impact: number;
  };
  analyzer: {
    version: string;
    status: string;
  };
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  database: {
    status: 'healthy' | 'unhealthy';
  };
  redis: {
    status: 'healthy' | 'unhealthy';
  };
  uptime_seconds: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
