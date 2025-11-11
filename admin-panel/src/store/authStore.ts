import { create } from 'zustand';
import { AuthState, User } from '../types';

interface AuthStore extends AuthState {
  login: (token: string, user: User) => void;
  logout: () => void;
  setUser: (user: User) => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: localStorage.getItem('auth_token'),
  isAuthenticated: !!localStorage.getItem('auth_token'),

  login: (token, user) => {
    localStorage.setItem('auth_token', token);
    set({ token, user, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem('auth_token');
    set({ token: null, user: null, isAuthenticated: false });
  },

  setUser: (user) => set({ user }),
}));
