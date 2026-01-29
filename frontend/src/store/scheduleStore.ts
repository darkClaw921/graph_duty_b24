import { create } from 'zustand';
import { DutyScheduleWithUsers } from '../types/schedule';
import { scheduleApi } from '../services/scheduleApi';

interface ScheduleState {
  schedules: DutyScheduleWithUsers[];
  loading: boolean;
  error: string | null;
  currentDateRange: { startDate?: string; endDate?: string } | null;
  fetchSchedules: (startDate?: string, endDate?: string) => Promise<void>;
  createSchedule: (data: { date: string; user_ids: number[] }, startDate?: string, endDate?: string) => Promise<void>;
  updateSchedule: (id: number, data: { user_ids?: number[] }, startDate?: string, endDate?: string) => Promise<void>;
  deleteSchedule: (id: number, startDate?: string, endDate?: string) => Promise<void>;
  generateSchedule: (year: number, month: number) => Promise<void>;
}

export const useScheduleStore = create<ScheduleState>((set, get) => ({
  schedules: [],
  loading: false,
  error: null,
  currentDateRange: null,

  fetchSchedules: async (startDate?, endDate?) => {
    set({ loading: true, error: null, currentDateRange: { startDate, endDate } });
    try {
      const schedules = await scheduleApi.getAll(startDate, endDate);
      set({ schedules, loading: false });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Ошибка загрузки графика', loading: false });
    }
  },

  createSchedule: async (data, startDate?, endDate?) => {
    const state = get();
    
    try {
      await scheduleApi.create(data);
      // Перезагружаем только для текущего диапазона дат
      const dateRange = startDate && endDate ? { startDate, endDate } : state.currentDateRange;
      if (dateRange) {
        const schedules = await scheduleApi.getAll(dateRange.startDate, dateRange.endDate);
        set({ schedules, loading: false });
      } else {
        set({ loading: false });
      }
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Ошибка создания записи',
        loading: false 
      });
      throw error;
    }
  },

  updateSchedule: async (id, data, startDate?, endDate?) => {
    const state = get();
    
    try {
      await scheduleApi.update(id, data);
      // Перезагружаем только для текущего диапазона дат
      const dateRange = startDate && endDate ? { startDate, endDate } : state.currentDateRange;
      if (dateRange) {
        const schedules = await scheduleApi.getAll(dateRange.startDate, dateRange.endDate);
        set({ schedules, loading: false });
      } else {
        set({ loading: false });
      }
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Ошибка обновления записи',
        loading: false 
      });
      throw error;
    }
  },

  deleteSchedule: async (id, _startDate?, _endDate?) => {
    const state = get();
    
    try {
      await scheduleApi.delete(id);
      // Оптимистичное обновление - удаляем из списка сразу
      const updatedSchedules = state.schedules.filter((s) => s.id !== id);
      set({ 
        schedules: updatedSchedules,
        loading: false 
      });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Ошибка удаления записи',
        loading: false 
      });
      throw error;
    }
  },

  generateSchedule: async (year, month) => {
    set({ loading: true, error: null });
    try {
      await scheduleApi.generate(year, month);
      await scheduleApi.getAll().then((schedules) => set({ schedules, loading: false }));
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Ошибка генерации графика', loading: false });
      throw error;
    }
  },
}));
