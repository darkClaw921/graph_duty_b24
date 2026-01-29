export interface User {
  id: number;
  name: string | null;
  last_name: string | null;
  email: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  id: number;
  name?: string | null;
  last_name?: string | null;
  email?: string | null;
  active?: boolean;
}
