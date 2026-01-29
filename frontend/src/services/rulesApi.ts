import { api } from './api';
import { UpdateRule, UpdateRuleCreate, UpdateRuleUpdate } from '../types/rule';

export const rulesApi = {
  getAll: async (): Promise<UpdateRule[]> => {
    const response = await api.get<UpdateRule[]>('/api/settings/rules');
    return response.data;
  },

  getById: async (ruleId: number): Promise<UpdateRule> => {
    const response = await api.get<UpdateRule>(`/api/settings/rules/${ruleId}`);
    return response.data;
  },

  create: async (data: UpdateRuleCreate): Promise<UpdateRule> => {
    const response = await api.post<UpdateRule>('/api/settings/rules', data);
    return response.data;
  },

  update: async (ruleId: number, data: UpdateRuleUpdate): Promise<UpdateRule> => {
    const response = await api.put<UpdateRule>(`/api/settings/rules/${ruleId}`, data);
    return response.data;
  },

  delete: async (ruleId: number): Promise<void> => {
    await api.delete(`/api/settings/rules/${ruleId}`);
  },

  getUsers: async (ruleId: number): Promise<number[]> => {
    const response = await api.get<number[]>(`/api/settings/rules/${ruleId}/users`);
    return response.data;
  },

  addUser: async (ruleId: number, userId: number): Promise<void> => {
    await api.post(`/api/settings/rules/${ruleId}/users/${userId}`);
  },

  removeUser: async (ruleId: number, userId: number): Promise<void> => {
    await api.delete(`/api/settings/rules/${ruleId}/users/${userId}`);
  },
};
