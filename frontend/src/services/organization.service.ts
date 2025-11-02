/**
 * Organization Service
 * 
 * Handles organization management API calls
 */

import api from './api';
import type { Organization } from '../types';

export const organizationService = {
  /**
   * List all organizations (superuser only)
   */
  async list(): Promise<Organization[]> {
    const response = await api.get('/api/v1/organizations');
    return response.data;
  },

  /**
   * Get organization by ID
   */
  async get(id: string): Promise<Organization> {
    const response = await api.get(`/api/v1/organizations/${id}`);
    return response.data;
  },

  /**
   * Create new organization (superuser only)
   */
  async create(data: {
    name: string;
    slug: string;
    description?: string;
  }): Promise<Organization> {
    const response = await api.post('/api/v1/organizations', data);
    return response.data;
  },

  /**
   * Update organization
   */
  async update(
    id: string,
    data: {
      name?: string;
      description?: string;
      is_active?: boolean;
    }
  ): Promise<Organization> {
    const response = await api.put(`/api/v1/organizations/${id}`, data);
    return response.data;
  },

  /**
   * Delete organization
   */
  async delete(id: string): Promise<void> {
    await api.delete(`/api/v1/organizations/${id}`);
  },
};
