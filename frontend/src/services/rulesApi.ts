import { api } from './api';
import { UpdateRule, UpdateRuleCreate, UpdateRuleUpdate } from '../types/rule';

export const rulesApi = {
  getAll: async (): Promise<UpdateRule[]> => {
    const response = await api.get<UpdateRule[]>('/settings/rules');
    return response.data;
  },

  getById: async (ruleId: number): Promise<UpdateRule> => {
    const response = await api.get<UpdateRule>(`/settings/rules/${ruleId}`);
    return response.data;
  },

  create: async (data: UpdateRuleCreate): Promise<UpdateRule> => {
    const response = await api.post<UpdateRule>('/settings/rules', data);
    return response.data;
  },

  update: async (ruleId: number, data: UpdateRuleUpdate): Promise<UpdateRule> => {
    const response = await api.put<UpdateRule>(`/settings/rules/${ruleId}`, data);
    return response.data;
  },

  delete: async (ruleId: number): Promise<void> => {
    await api.delete(`/settings/rules/${ruleId}`);
  },

  getUsers: async (ruleId: number): Promise<number[]> => {
    const response = await api.get<number[]>(`/settings/rules/${ruleId}/users`);
    return response.data;
  },

  addUser: async (ruleId: number, userId: number): Promise<void> => {
    await api.post(`/settings/rules/${ruleId}/users/${userId}`);
  },

  removeUser: async (ruleId: number, userId: number): Promise<void> => {
    await api.delete(`/settings/rules/${ruleId}/users/${userId}`);
  },
};
