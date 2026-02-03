import { api } from './api';
import { UpdateHistory, UpdateHistoryFilters, UpdateHistoryCount } from '../types/history';

export const historyApi = {
  getAll: async (filters: UpdateHistoryFilters = {}): Promise<UpdateHistory[]> => {
    const params: Record<string, string | number> = {};
    
    if (filters.entity_type) params.entity_type = filters.entity_type;
    if (filters.entity_id !== undefined) params.entity_id = filters.entity_id;
    if (filters.start_date) params.start_date = filters.start_date;
    if (filters.end_date) params.end_date = filters.end_date;
    if (filters.update_source) params.update_source = filters.update_source;
    if (filters.skip !== undefined) params.skip = filters.skip;
    if (filters.limit !== undefined) params.limit = filters.limit;
    
    const response = await api.get<UpdateHistory[]>('/history', { params });
    return response.data;
  },

  getCount: async (filters: Omit<UpdateHistoryFilters, 'skip' | 'limit'> = {}): Promise<UpdateHistoryCount> => {
    const params: Record<string, string | number> = {};
    
    if (filters.entity_type) params.entity_type = filters.entity_type;
    if (filters.entity_id !== undefined) params.entity_id = filters.entity_id;
    if (filters.start_date) params.start_date = filters.start_date;
    if (filters.end_date) params.end_date = filters.end_date;
    if (filters.update_source) params.update_source = filters.update_source;
    
    const response = await api.get<UpdateHistoryCount>('/history/count', { params });
    return response.data;
  },

  getUserEntityStats: async (date: string, userId: number): Promise<Record<string, number>> => {
    const response = await api.get<Record<string, number>>(`/history/stats/${date}/${userId}`);
    return response.data;
  },
};
