/**
 * Type definitions for AI Query Analyzer frontend
 */

export interface SlowQuery {
  id: string;  // Representative query ID (most recent execution)
  fingerprint: string;
  execution_count: number;
  avg_duration_ms: number;
  p95_duration_ms: number;
  max_duration_ms: number;
  min_duration_ms: number;
  source_db_type: string;
  source_db_host: string;
  last_seen: string;
  has_analysis: boolean;
  max_improvement_level?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}

export interface SlowQueryDetail {
  id: string;
  source_db_type: string;
  source_db_host: string;
  source_db_name: string;
  fingerprint: string;
  full_sql: string;
  sql_hash: string;
  duration_ms: number | string;  // Backend returns as string (Decimal)
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
  confidence_score: number | string;  // Backend returns as string (Decimal)
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

export interface TableImpact {
  source_db_type: string;
  source_db_host: string;
  table_name: string;
  query_count: number;
  avg_duration_ms: number;
  distinct_queries: number;
}

export interface ImprovementSummary {
  improvement_level: string;
  count: number;
  avg_potential_speedup?: string | null;
}

export interface QueryTrend {
  date: string;
  query_count: number;
  avg_duration_ms: number;
  max_duration_ms: number;
}

export interface StatsResponse {
  total_slow_queries: number;
  total_analyzed: number;
  total_pending: number;
  databases_monitored: number;
  top_tables: TableImpact[];
  improvement_summary: ImprovementSummary[];
  recent_trend: QueryTrend[];
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

// Authentication types
export interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  organization_id: number;
  identity_id: number;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
}

// Collector Agent types (new multi-tenant system)
export interface CollectorAgent {
  id: number;
  organization_id: number;
  team_id: number;
  name: string;
  type: 'mysql' | 'postgres';
  status: 'online' | 'offline' | 'stopped' | 'error' | 'starting';
  config: {
    host: string;
    port: number;
    user: string;
    password?: string;
    database?: string;
    databases?: string[];
    min_exec_time_ms?: number;
  };
  last_heartbeat?: string;
  last_collection?: string;
  last_error?: string;
  stats: {
    queries_collected?: number;
    errors_count?: number;
    uptime_seconds?: number;
    last_error?: string;
  };
  collection_interval_minutes: number;
  auto_collect: boolean;
  is_online: boolean;
  created_at: string;
  updated_at?: string;
}

export interface CollectorAgentCommand {
  id: number;
  command: 'start' | 'stop' | 'collect' | 'update_config';
  params: Record<string, any>;
  executed: boolean;
  executed_at?: string;
  result: Record<string, any>;
  created_at: string;
  expires_at: string;
}

export interface CollectorAgentCreateRequest {
  name: string;
  type: 'mysql' | 'postgres';
  team_id: number;
  config: {
    host: string;
    port: number;
    user: string;
    password: string;
    database?: string;
    databases?: string[];
    min_exec_time_ms?: number;
  };
  collection_interval_minutes: number;
  auto_collect: boolean;
}

// Organization types
export interface Organization {
  id: number;
  name: string;
  settings: Record<string, any>;
  api_key_created_at?: string;
  api_key_expires_at?: string;
  created_at: string;
  updated_at: string;
}

export interface OrganizationCreateRequest {
  name: string;
  settings?: Record<string, any>;
}
