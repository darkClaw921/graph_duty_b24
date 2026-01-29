import { create } from 'zustand';
import { authApi } from '../services/authApi';

const TOKEN_KEY = 'auth_token';

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem(TOKEN_KEY),
  isAuthenticated: !!localStorage.getItem(TOKEN_KEY),

  login: async (username: string, password: string) => {
    try {
      const response = await authApi.login(username, password);
      localStorage.setItem(TOKEN_KEY, response.access_token);
      set({ token: response.access_token, isAuthenticated: true });
    } catch (error) {
      throw error;
    }
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
    set({ token: null, isAuthenticated: false });
  },

  checkAuth: () => {
    const token = localStorage.getItem(TOKEN_KEY);
    set({ token, isAuthenticated: !!token });
  },
}));
