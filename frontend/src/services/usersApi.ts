import { api } from './api';
import { User } from '../types/user';

export const usersApi = {
  getAll: async (skip = 0, limit = 100): Promise<User[]> => {
    const response = await api.get<User[]>('/api/users', {
      params: { skip, limit },
    });
    return response.data;
  },

  getById: async (userId: number): Promise<User> => {
    const response = await api.get<User>(`/api/users/${userId}`);
    return response.data;
  },

  sync: async (): Promise<{ message: string; created: number; updated: number; total: number }> => {
    const response = await api.post('/api/users/sync');
    return response.data;
  },

  toggleActive: async (userId: number): Promise<User> => {
    const response = await api.put<User>(`/api/users/${userId}/toggle-active`);
    return response.data;
  },
};
