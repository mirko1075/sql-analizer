/**
 * Onboarding Service
 *
 * Handles the onboarding wizard flow for new customers
 */

import api from './api';

export interface OnboardingStartRequest {
  organization_name: string;
  organization_slug?: string;
  team_name: string;
  collector_name: string;
  collector_hostname?: string;
}

export interface OnboardingStartResponse {
  success: boolean;
  organization_id: string;
  team_id: string;
  collector_id: string;
  agent_token: string;
  docker_command: string;
}

export interface DatabaseConfig {
  name: string;
  db_type: 'mysql' | 'postgres';
  host: string;
  port: number;
  database_name: string;
  username: string;
  password: string;
  ssl_enabled?: boolean;
  ssl_ca?: string | null;
}

export interface OnboardingDatabasesRequest {
  collector_id: string;
  databases: DatabaseConfig[];
}

export interface OnboardingDatabasesResponse {
  success: boolean;
  databases_added: number;
  databases_failed: number;
  database_ids: string[];
  errors: string[];
}

export interface DatabaseConnectionStatus {
  id: string;
  name: string;
  db_type: string;
  host: string;
  port: number;
  database_name: string;
  status: 'PENDING' | 'CONNECTED' | 'ERROR';
  last_connected_at: string | null;
  error_message: string | null;
}

export interface OnboardingStatusResponse {
  collector_id: string;
  collector_name: string;
  collector_status: 'ACTIVE' | 'INACTIVE' | 'ERROR';
  last_heartbeat: string | null;
  databases: DatabaseConnectionStatus[];
  total_databases: number;
  connected_databases: number;
  pending_databases: number;
  error_databases: number;
}

export interface OnboardingCompleteRequest {
  collector_id: string;
}

export interface OnboardingCompleteResponse {
  success: boolean;
  message: string;
  collector_id: string;
  collector_status: string;
  databases_configured: number;
  next_steps: string[];
}

export const onboardingService = {
  /**
   * Start the onboarding process
   * Creates organization, team, and collector
   */
  async start(data: OnboardingStartRequest): Promise<OnboardingStartResponse> {
    const response = await api.post('/api/v1/onboarding/start', data);
    return response.data;
  },

  /**
   * Add databases to the collector
   */
  async addDatabases(data: OnboardingDatabasesRequest): Promise<OnboardingDatabasesResponse> {
    const response = await api.post('/api/v1/onboarding/databases', data);
    return response.data;
  },

  /**
   * Get onboarding status
   */
  async getStatus(collectorId: string): Promise<OnboardingStatusResponse> {
    const response = await api.get(`/api/v1/onboarding/status/${collectorId}`);
    return response.data;
  },

  /**
   * Complete the onboarding process
   */
  async complete(data: OnboardingCompleteRequest): Promise<OnboardingCompleteResponse> {
    const response = await api.post('/api/v1/onboarding/complete', data);
    return response.data;
  },
};

export default onboardingService;
