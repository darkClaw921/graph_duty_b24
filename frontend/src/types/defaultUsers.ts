export interface DefaultUser {
  id: number;
  user_id: number;
  position: number;
  created_at: string;
}

export interface DefaultUserWithUser extends DefaultUser {
  user_name: string | null;
  user_email: string | null;
}

export interface DefaultUserCreate {
  user_id: number;
  position?: number;
}

export interface DefaultUsersReorder {
  user_ids: number[];
}
