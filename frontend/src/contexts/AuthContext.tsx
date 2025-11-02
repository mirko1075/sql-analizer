/**
 * Authentication Context
 * 
 * Provides authentication state and methods throughout the application.
 * Handles token management, user state, and session persistence.
 */

import React, { createContext, useState, useEffect, useCallback } from 'react';
import { authService } from '../services/auth.service';
import { setAuthToken } from '../services/api';
import type { User, AuthContextType, AuthState } from '../types';

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_STORAGE_KEY = 'auth_tokens';
const USER_STORAGE_KEY = 'auth_user';

interface StoredTokens {
  accessToken: string;
  refreshToken: string;
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AuthState>({
    user: null,
    accessToken: null,
    refreshToken: null,
    isAuthenticated: false,
    isLoading: true,
  });

  const clearAuth = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
    setAuthToken(null);
    setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
    });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    try {
      const tokens = await authService.login({ email, password });
      
      // Set token in API client
      setAuthToken(tokens.access_token);

      // Fetch user info
      const user = await authService.getCurrentUser();

      // Store tokens and user
      localStorage.setItem(
        TOKEN_STORAGE_KEY,
        JSON.stringify({
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
        })
      );
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));

      setState({
        user,
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  }, []);

  const register = useCallback(
    async (email: string, password: string, fullName: string) => {
      try {
        const tokens = await authService.register({
          email,
          password,
          full_name: fullName,
        });

        // Set token in API client
        setAuthToken(tokens.access_token);

        // Fetch user info
        const user = await authService.getCurrentUser();

        // Store tokens and user
        localStorage.setItem(
          TOKEN_STORAGE_KEY,
          JSON.stringify({
            accessToken: tokens.access_token,
            refreshToken: tokens.refresh_token,
          })
        );
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));

        setState({
          user,
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          isAuthenticated: true,
          isLoading: false,
        });
      } catch (error) {
        console.error('Register error:', error);
        throw error;
      }
    },
    []
  );

  const logout = useCallback(async () => {
    try {
      // Call logout endpoint to revoke session
      await authService.logout();
    } catch (error) {
      console.error('Logout API error:', error);
      // Continue with local logout even if API fails
    } finally {
      clearAuth();
    }
  }, [clearAuth]);

  // Load tokens and user from localStorage on mount
  useEffect(() => {
    const initAuth = async () => {
      try {
        const storedTokens = localStorage.getItem(TOKEN_STORAGE_KEY);
        const storedUser = localStorage.getItem(USER_STORAGE_KEY);

        if (storedTokens && storedUser) {
          const tokens: StoredTokens = JSON.parse(storedTokens);

          // Set token in API client
          setAuthToken(tokens.accessToken);

          // Try to verify token by fetching current user
          try {
            const currentUser = await authService.getCurrentUser();
            setState({
              user: currentUser,
              accessToken: tokens.accessToken,
              refreshToken: tokens.refreshToken,
              isAuthenticated: true,
              isLoading: false,
            });
          } catch {
            // Token invalid, try to refresh
            try {
              const newTokens = await authService.refreshToken(tokens.refreshToken);
              setAuthToken(newTokens.access_token);
              
              const currentUser = await authService.getCurrentUser();
              
              // Store new tokens
              localStorage.setItem(
                TOKEN_STORAGE_KEY,
                JSON.stringify({
                  accessToken: newTokens.access_token,
                  refreshToken: newTokens.refresh_token,
                })
              );
              
              setState({
                user: currentUser,
                accessToken: newTokens.access_token,
                refreshToken: newTokens.refresh_token,
                isAuthenticated: true,
                isLoading: false,
              });
            } catch (refreshError) {
              // Refresh failed, clear auth
              console.error('Token refresh failed:', refreshError);
              clearAuth();
            }
          }
        } else {
          setState(prev => ({ ...prev, isLoading: false }));
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
        clearAuth();
      }
    };

    initAuth();
  }, [clearAuth]);

  // Listen for unauthorized events from API
  useEffect(() => {
    const handleUnauthorized = () => {
      console.warn('Unauthorized access detected, logging out...');
      logout();
    };

    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, [logout]);

  const refreshAccessToken = useCallback(async () => {
    if (!state.refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      const newTokens = await authService.refreshToken(state.refreshToken);
      
      setAuthToken(newTokens.access_token);

      // Update stored tokens
      localStorage.setItem(
        TOKEN_STORAGE_KEY,
        JSON.stringify({
          accessToken: newTokens.access_token,
          refreshToken: newTokens.refresh_token,
        })
      );

      setState(prev => ({
        ...prev,
        accessToken: newTokens.access_token,
        refreshToken: newTokens.refresh_token,
      }));
    } catch (error) {
      console.error('Token refresh error:', error);
      clearAuth();
      throw error;
    }
  }, [state.refreshToken, clearAuth]);

  const updateUser = useCallback((updates: Partial<User>) => {
    setState(prev => {
      if (!prev.user) return prev;

      const updatedUser = { ...prev.user, ...updates };
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(updatedUser));

      return {
        ...prev,
        user: updatedUser,
      };
    });
  }, []);

  const value: AuthContextType = {
    ...state,
    login,
    register,
    logout,
    refreshAccessToken,
    updateUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
