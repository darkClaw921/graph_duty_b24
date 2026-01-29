import { api } from './api';
import { LoginRequest, LoginResponse } from '../types/auth';

export const authApi = {
  login: async (username: string, password: string): Promise<LoginResponse> => {
    const response = await api.post<LoginResponse>('/api/auth/login', {
      username,
      password,
    } as LoginRequest);
    return response.data;
  },
};
