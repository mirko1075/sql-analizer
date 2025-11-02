/**
 * Database Connection Service
 * 
 * Handles database connection management
 */

import api from './api';
import type { DatabaseConnection, DatabaseType } from '../types';

export const databaseConnectionService = {
  /**
   * List all database connections (filtered by team)
   */
  async list(): Promise<DatabaseConnection[]> {
    const response = await api.get('/api/v1/database-connections');
    return response.data.connections || response.data;
  },

  /**
   * Get database connection by ID
   */
  async get(id: string): Promise<DatabaseConnection> {
    const response = await api.get(`/api/v1/database-connections/${id}`);
    return response.data;
  },

  /**
   * Create new database connection
   */
  async create(data: {
    name: string;
    db_type: DatabaseType;
    host: string;
    port: number;
    database: string;
    username: string;
    password: string;
    team_id: string;
    description?: string;
    ssl_enabled?: boolean;
  }): Promise<DatabaseConnection> {
    const response = await api.post('/api/v1/database-connections', data);
    return response.data;
  },

  /**
   * Update database connection
   */
  async update(
    id: string,
    data: {
      name?: string;
      host?: string;
      port?: number;
      database?: string;
      username?: string;
      password?: string;
      description?: string;
      ssl_enabled?: boolean;
      is_active?: boolean;
    }
  ): Promise<DatabaseConnection> {
    const response = await api.put(`/api/v1/database-connections/${id}`, data);
    return response.data;
  },

  /**
   * Delete database connection
   */
  async delete(id: string): Promise<void> {
    await api.delete(`/api/v1/database-connections/${id}`);
  },

  /**
   * Test database connection
   */
  async test(id: string): Promise<{ success: boolean; message?: string; error?: string }> {
    const response = await api.post(`/api/v1/database-connections/${id}/test`);
    return response.data;
  },
};
