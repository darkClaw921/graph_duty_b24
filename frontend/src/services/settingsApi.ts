import { api } from './api';
import {
  DefaultUserWithUser,
  DefaultUserCreate,
  DefaultUsersReorder,
} from '../types/defaultUsers';
import { EntityField } from '../types/entity';

export const settingsApi = {
  // Дефолтные пользователи
  getDefaultUsers: async (): Promise<DefaultUserWithUser[]> => {
    const response = await api.get<DefaultUserWithUser[]>('/settings/default-users');
    return response.data;
  },

  createDefaultUser: async (data: DefaultUserCreate): Promise<void> => {
    await api.post('/settings/default-users', data);
  },

  deleteDefaultUser: async (id: number): Promise<void> => {
    await api.delete(`/settings/default-users/${id}`);
  },

  reorderDefaultUsers: async (data: DefaultUsersReorder): Promise<void> => {
    await api.put('/settings/default-users/reorder', data);
  },

  // Поля сущностей (для правил)
  getEntityFields: async (ruleId: number): Promise<{ entity_type: string; fields: EntityField; cached_at: string }> => {
    const response = await api.get(`/settings/rules/${ruleId}/fields`);
    return response.data;
  },

  // Поля сущностей по типу
  getEntityFieldsByType: async (entityType: string): Promise<{ entity_type: string; fields: EntityField; cached_at: string }> => {
    const response = await api.get(`/settings/entity-types/${entityType}/fields`);
    return response.data;
  },

  // Значения поля (статусы, категории)
  getFieldValues: async (entityType: string, fieldId: string): Promise<{ field_id: string; field_type: string; values: Array<{ id: string; name: string; semantics?: string }> }> => {
    const response = await api.get(`/settings/entity-types/${entityType}/fields/${fieldId}/values`);
    return response.data;
  },

  // Стадии категории
  getCategoryStages: async (entityType: string, fieldId: string, categoryId: number): Promise<{ field_id: string; category_id: number; values: Array<{ id: string; name: string; semantics?: string }> }> => {
    const response = await api.get(`/settings/entity-types/${entityType}/fields/${fieldId}/category/${categoryId}/stages`);
    return response.data;
  },

  // Webhook
  getWebhookUrl: async (): Promise<{ webhook_url: string }> => {
    const response = await api.get('/settings/webhook');
    return response.data;
  },
};
