/**
 * Team Service
 * 
 * Handles team management and member operations
 */

import api from './api';
import type { Team, TeamMember, UserRole } from '../types';

export const teamService = {
  /**
   * List all teams user has access to
   */
  async list(): Promise<Team[]> {
    const response = await api.get('/api/v1/teams');
    return response.data;
  },

  /**
   * Get team by ID
   */
  async get(id: string): Promise<Team> {
    const response = await api.get(`/api/v1/teams/${id}`);
    return response.data;
  },

  /**
   * Create new team
   */
  async create(data: {
    name: string;
    slug: string;
    organization_id: string;
    description?: string;
  }): Promise<Team> {
    const response = await api.post('/api/v1/teams', data);
    return response.data;
  },

  /**
   * Update team
   */
  async update(
    id: string,
    data: {
      name?: string;
      description?: string;
      is_active?: boolean;
    }
  ): Promise<Team> {
    const response = await api.put(`/api/v1/teams/${id}`, data);
    return response.data;
  },

  /**
   * Delete team
   */
  async delete(id: string): Promise<void> {
    await api.delete(`/api/v1/teams/${id}`);
  },

  // =============================================================================
  // Team Members
  // =============================================================================

  /**
   * List team members
   */
  async listMembers(teamId: string): Promise<TeamMember[]> {
    const response = await api.get(`/api/v1/teams/${teamId}/members`);
    return response.data;
  },

  /**
   * Add member to team
   */
  async addMember(
    teamId: string,
    data: {
      user_id: string;
      role: UserRole;
    }
  ): Promise<TeamMember> {
    const response = await api.post(`/api/v1/teams/${teamId}/members`, data);
    return response.data;
  },

  /**
   * Update team member role
   */
  async updateMemberRole(
    teamId: string,
    userId: string,
    role: UserRole
  ): Promise<TeamMember> {
    const response = await api.put(`/api/v1/teams/${teamId}/members/${userId}`, {
      role,
    });
    return response.data;
  },

  /**
   * Remove member from team
   */
  async removeMember(teamId: string, userId: string): Promise<void> {
    await api.delete(`/api/v1/teams/${teamId}/members/${userId}`);
  },
};
