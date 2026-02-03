import { api } from './api';
import { DutySchedule, DutyScheduleWithUsers, DutyScheduleCreate, DutyScheduleUpdate } from '../types/schedule';

export const scheduleApi = {
  getAll: async (startDate?: string, endDate?: string): Promise<DutyScheduleWithUsers[]> => {
    const params: Record<string, string> = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    
    const response = await api.get<DutyScheduleWithUsers[]>('/schedule', { params });
    return response.data;
  },

  getByDate: async (date: string): Promise<DutyScheduleWithUsers> => {
    const response = await api.get<DutyScheduleWithUsers>(`/schedule/${date}`);
    return response.data;
  },

  create: async (data: DutyScheduleCreate): Promise<DutySchedule> => {
    const response = await api.post<DutySchedule>('/schedule', data);
    return response.data;
  },

  update: async (id: number, data: DutyScheduleUpdate): Promise<DutySchedule> => {
    const response = await api.put<DutySchedule>(`/schedule/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/schedule/${id}`);
  },

  generate: async (year: number, month: number): Promise<{ message: string; count: number }> => {
    const response = await api.post('/schedule/generate', null, {
      params: { year, month },
    });
    return response.data;
  },

  getStats: async (date: string): Promise<Record<number, number>> => {
    const response = await api.get<Record<number, number>>(`/schedule/stats/${date}`);
    return response.data;
  },
};
