import { create } from 'zustand';
import { DefaultUserWithUser } from '../types/defaultUsers';
import { settingsApi } from '../services/settingsApi';

interface SettingsState {
  defaultUsers: DefaultUserWithUser[];
  loading: boolean;
  error: string | null;
  fetchDefaultUsers: () => Promise<void>;
  createDefaultUser: (data: { user_id: number }) => Promise<void>;
  deleteDefaultUser: (id: number) => Promise<void>;
  reorderDefaultUsers: (userIds: number[]) => Promise<void>;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  defaultUsers: [],
  loading: false,
  error: null,

  fetchDefaultUsers: async () => {
    set({ loading: true, error: null });
    try {
      const users = await settingsApi.getDefaultUsers();
      set({ defaultUsers: users, loading: false });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Ошибка загрузки дефолтных пользователей', loading: false });
    }
  },

  createDefaultUser: async (data) => {
    set({ loading: true, error: null });
    try {
      await settingsApi.createDefaultUser(data);
      await settingsApi.getDefaultUsers().then((users) => set({ defaultUsers: users, loading: false }));
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Ошибка добавления пользователя', loading: false });
      throw error;
    }
  },

  deleteDefaultUser: async (id) => {
    set({ loading: true, error: null });
    try {
      await settingsApi.deleteDefaultUser(id);
      set((state) => ({
        defaultUsers: state.defaultUsers.filter((u) => u.id !== id),
        loading: false,
      }));
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Ошибка удаления пользователя', loading: false });
      throw error;
    }
  },

  reorderDefaultUsers: async (userIds) => {
    set({ loading: true, error: null });
    try {
      await settingsApi.reorderDefaultUsers({ user_ids: userIds });
      await settingsApi.getDefaultUsers().then((users) => set({ defaultUsers: users, loading: false }));
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Ошибка изменения порядка', loading: false });
      throw error;
    }
  },
}));
