/**
 * Authentication Service
 * 
 * Handles all authentication-related API calls including:
 * - Login/Register
 * - Token management
 * - User profile
 * - Session management
 */

import api from './api';
import type {
  User,
  TokenResponse,
  LoginRequest,
  RegisterRequest,
} from '../types';

interface UserSession {
  id: string;
  token_type: string;
  created_at: string;
  expires_at: string;
  last_used_at?: string;
  ip_address?: string;
  user_agent?: string;
}

const AUTH_ENDPOINTS = {
  REGISTER: '/auth/register',
  LOGIN: '/auth/login',
  LOGOUT: '/auth/logout',
  REFRESH: '/auth/refresh',
  ME: '/auth/me',
};

export const authService = {
  /**
   * Register a new user
   */
  async register(data: RegisterRequest): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>(AUTH_ENDPOINTS.REGISTER, data);
    return response.data;
  },

  /**
   * Login with email and password
   */
  async login(data: LoginRequest): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>(AUTH_ENDPOINTS.LOGIN, data);
    return response.data;
  },

  /**
   * Logout (revokes current session)
   */
  async logout(): Promise<void> {
    await api.post(AUTH_ENDPOINTS.LOGOUT);
  },

  /**
   * Refresh access token using refresh token
   */
  async refreshToken(refreshToken: string): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>(AUTH_ENDPOINTS.REFRESH, {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  /**
   * Get current user info
   */
  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>(AUTH_ENDPOINTS.ME);
    return response.data;
  },

  /**
   * Update user profile
   */
  async updateProfile(updates: {
    full_name?: string;
    preferences?: Record<string, unknown>;
  }): Promise<User> {
    const response = await api.put<User>('/users/profile', updates);
    return response.data;
  },

  /**
   * Change password
   */
  async changePassword(
    currentPassword: string,
    newPassword: string
  ): Promise<void> {
    await api.post('/users/password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  },

  /**
   * Get user sessions
   */
  async getSessions(): Promise<UserSession[]> {
    const response = await api.get('/users/sessions');
    return response.data.sessions || response.data;
  },

  /**
   * Revoke a session
   */
  async revokeSession(sessionId: string): Promise<void> {
    await api.delete(`/users/sessions/${sessionId}`);
  },
};
