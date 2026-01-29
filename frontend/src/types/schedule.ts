export interface DutyScheduleUserInfo {
  user_id: number;
  user_name: string | null;
  user_email: string | null;
}

export interface DutySchedule {
  id: number;
  date: string;
  users: DutyScheduleUserInfo[];
  created_at: string;
  updated_at: string;
}

export interface DutyScheduleWithUsers extends DutySchedule {
  users: DutyScheduleUserInfo[];
}

export interface DutyScheduleCreate {
  date: string;
  user_ids: number[];
}

export interface DutyScheduleUpdate {
  user_ids?: number[];
}
