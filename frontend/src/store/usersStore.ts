import { create } from 'zustand';
import { User } from '../types/user';
import { usersApi } from '../services/usersApi';

interface UsersState {
  users: User[];
  loading: boolean;
  error: string | null;
  fetchUsers: () => Promise<void>;
  syncUsers: () => Promise<{ created: number; updated: number; total: number }>;
  toggleUserActive: (userId: number) => Promise<void>;
}

export const useUsersStore = create<UsersState>((set) => ({
  users: [],
  loading: false,
  error: null,

  fetchUsers: async () => {
    set({ loading: true, error: null });
    try {
      const users = await usersApi.getAll();
      set({ users, loading: false });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Ошибка загрузки пользователей', loading: false });
    }
  },

  syncUsers: async () => {
    set({ loading: true, error: null });
    try {
      const result = await usersApi.sync();
      await usersApi.getAll().then((users) => set({ users, loading: false }));
      return result;
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Ошибка синхронизации', loading: false });
      throw error;
    }
  },

  toggleUserActive: async (userId: number) => {
    set({ error: null });
    try {
      const updatedUser = await usersApi.toggleActive(userId);
      set((state) => ({
        users: state.users.map((user) => (user.id === userId ? updatedUser : user)),
      }));
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Ошибка обновления статуса' });
      throw error;
    }
  },
}));
