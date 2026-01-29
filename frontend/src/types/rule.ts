export interface UserDistribution {
  user_id: number;
  distribution_percentage: number;
}

export interface UpdateRule {
  id: number;
  entity_type: string;
  entity_name: string;
  rule_type: 'assigned_by_condition' | 'field_condition' | 'combined';
  condition_config: Record<string, any>;
  priority: number;
  enabled: boolean;
  update_time: string;
  update_days: number[] | null;
  user_distributions: UserDistribution[];
  user_ids: number[]; // Для обратной совместимости
  distribution_percentage?: number; // Устаревшее поле
  update_related_contacts_companies?: boolean; // Обновлять также связанные контакты и компании (только для deal)
  created_at: string;
  updated_at: string;
}

export interface UpdateRuleCreate {
  entity_type: string;
  entity_name: string;
  rule_type: 'assigned_by_condition' | 'field_condition' | 'combined';
  condition_config: Record<string, any>;
  priority?: number;
  enabled?: boolean;
  update_time: string;
  update_days?: number[] | null;
  user_distributions?: UserDistribution[];
  user_ids?: number[]; // Для обратной совместимости
  update_related_contacts_companies?: boolean; // Обновлять также связанные контакты и компании (только для deal)
}

export interface UpdateRuleUpdate {
  entity_type?: string;
  entity_name?: string;
  rule_type?: 'assigned_by_condition' | 'field_condition' | 'combined';
  condition_config?: Record<string, any>;
  priority?: number;
  enabled?: boolean;
  update_time?: string;
  update_days?: number[] | null;
  user_distributions?: UserDistribution[];
  user_ids?: number[]; // Для обратной совместимости
  update_related_contacts_companies?: boolean; // Обновлять также связанные контакты и компании (только для deal)
}
