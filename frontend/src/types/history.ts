export enum UpdateSource {
  WEBHOOK = 'webhook',
  SCHEDULED = 'scheduled',
  MANUAL = 'manual',
}

export interface UpdateHistory {
  id: number;
  entity_type: string;
  entity_id: number;
  old_assigned_by_id: number | null;
  new_assigned_by_id: number;
  update_source: UpdateSource;
  rule_id: number | null;
  related_entity_type: string | null;
  related_entity_id: number | null;
  created_at: string;
  old_user_name: string | null;
  new_user_name: string | null;
}

export interface UpdateHistoryFilters {
  entity_type?: string;
  entity_id?: number;
  start_date?: string;
  end_date?: string;
  update_source?: UpdateSource;
  skip?: number;
  limit?: number;
}

export interface UpdateHistoryCount {
  count: number;
}
