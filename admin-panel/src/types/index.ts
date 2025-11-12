// Core types for DBPower Admin Panel

export interface User {
  id: number;
  email: string;
  role: 'super_admin' | 'org_admin' | 'team_lead' | 'user';
  organization_id: number;
  team_id?: number;
  identity_id?: number;
  is_active: boolean;
}

export interface Organization {
  id: number;
  name: string;
  created_at: string;
  api_key_expires_at?: string;
}

export interface Team {
  id: number;
  organization_id: number;
  name: string;
  created_at: string;
}

export interface Identity {
  id: number;
  team_id: number;
  name: string;
  database_type: string;
  created_at: string;
}

export interface AnalysisResult {
  id: number;
  slow_query_id: number;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  summary: string;
  issues: string[];
  recommendations: string[];
  issues_found?: number;
  optimization_priority?: 'critical' | 'high' | 'medium' | 'low' | 'info';
  overall_assessment?: string;
  estimated_improvement?: string;
  ai_model_used?: string;
  created_at: string;
}

export interface SlowQuery {
  id: number;
  organization_id: number;
  team_id: number;
  identity_id: number;
  sql_text?: string;
  original_query?: string;
  anonymized_query?: string;
  execution_time_ms: number;
  database_type: 'mysql' | 'postgresql';
  rows_examined?: number;
  rows_returned?: number;
  created_at: string;
  analysis_result?: AnalysisResult;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
}

export interface DashboardStats {
  total_queries: number;
  total_issues: number;
  avg_execution_time: number;
  organizations_count: number;
  users_count: number;
}
