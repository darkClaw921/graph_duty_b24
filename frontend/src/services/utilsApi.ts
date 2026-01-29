import { api } from './api';

export interface UpdateCountResponse {
  date: string;
  total_count: number;
  rules: Array<{
    rule_id: number;
    rule_name: string;
    entity_type: string;
    count: number;
  }>;
}

export interface UpdateProgress {
  type: 'start' | 'progress' | 'complete';
  date?: string;
  total_rules?: number;
  duty_user_ids?: number[];
  duty_user_names?: string[];
  rule_id?: number;
  rule_name?: string;
  entity_type?: string;
  status?: 'processing' | 'completed' | 'skipped' | 'error';
  reason?: string;
  updated_count?: number;
  processed_rules?: number;
  error?: string;
  updated_entities?: number;
  errors?: string[];
}

export interface PreviewEntity {
  entity_id: number;
  entity_type: string;
  rule_id: number;
  rule_name: string;
  current_assigned_by_id: number | null;
  new_assigned_by_id: number;
  current_assigned_by_name?: string | null;
  new_assigned_by_name: string;
  related_entities?: Array<{
    entity_id: number;
    entity_type: string;
    current_assigned_by_id: number | null;
    current_assigned_by_name?: string | null;
    new_assigned_by_id: number;
    new_assigned_by_name: string;
  }>;
}

export interface PreviewUpdatesResponse {
  date: string;
  total_count: number;
  entities: PreviewEntity[];
}

export const utilsApi = {
  getUpdateCount: async (updateDate?: string): Promise<UpdateCountResponse> => {
    const params: Record<string, string> = {};
    if (updateDate) params.update_date = updateDate;
    
    const response = await api.get<UpdateCountResponse>('/utils/update-count', { params });
    return response.data;
  },

  updateNow: async (): Promise<{ date: string; updated_entities: number; errors: string[] }> => {
    const response = await api.post('/utils/update-now');
    return response.data;
  },

  updateNowStream: async (
    onProgress: (progress: UpdateProgress) => void,
    updateDate?: string
  ): Promise<void> => {
    const API_URL = import.meta.env.VITE_API_URL || '/api';
    const url = `${API_URL}/utils/update-now-stream${updateDate ? `?update_date=${updateDate}` : ''}`;
    
    // Получаем токен из localStorage для авторизации
    const TOKEN_KEY = 'auth_token';
    const token = localStorage.getItem(TOKEN_KEY);
    
    const headers: HeadersInit = {
      'Accept': 'text/event-stream',
    };
    
    // Добавляем токен авторизации, если он есть
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    console.log('Отправка запроса на:', url);
    
    const response = await fetch(url, {
      method: 'POST',
      headers,
    });
    
    console.log('Получен ответ:', response.status, response.statusText);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Ошибка ответа:', errorText);
      throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
    }
    
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    
    if (!reader) {
      throw new Error('Response body is not readable');
    }
    
    let buffer = '';
    let hasReceivedData = false;
    
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        console.log('Stream завершен, buffer:', buffer);
        if (!hasReceivedData && buffer) {
          // Попробуем обработать оставшийся буфер
          const lines = buffer.split('\n');
          for (const line of lines) {
            if (line.trim() && line.startsWith('data: ')) {
              try {
                const data = line.slice(6).trim();
                if (data) {
                  const progress: UpdateProgress = JSON.parse(data);
                  onProgress(progress);
                  hasReceivedData = true;
                }
              } catch (error) {
                console.error('Error parsing final buffer:', error, 'line:', line);
              }
            }
          }
        }
        break;
      }
      
      hasReceivedData = true;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      
      for (const line of lines) {
        const trimmedLine = line.trim();
        if (trimmedLine.startsWith('data: ')) {
          try {
            const data = trimmedLine.slice(6).trim(); // Remove 'data: ' prefix
            if (data) {
              console.log('Парсинг данных:', data);
              const progress: UpdateProgress = JSON.parse(data);
              console.log('Распарсенный прогресс:', progress);
              onProgress(progress);
              
              if (progress.type === 'complete') {
                console.log('Обновление завершено, выход из цикла');
                return;
              }
            }
          } catch (error) {
            console.error('Error parsing progress:', error, 'line:', trimmedLine);
          }
        } else if (trimmedLine && !trimmedLine.startsWith(':')) {
          // Если строка не пустая и не комментарий, попробуем распарсить как JSON
          try {
            const progress: UpdateProgress = JSON.parse(trimmedLine);
            console.log('Распарсенный прогресс (без префикса):', progress);
            onProgress(progress);
            if (progress.type === 'complete') {
              return;
            }
          } catch (error) {
            // Игнорируем ошибки парсинга для строк, которые не являются JSON
          }
        }
      }
    }
  },

  getPreviewUpdates: async (updateDate?: string): Promise<PreviewUpdatesResponse> => {
    const params: Record<string, string> = {};
    if (updateDate) params.update_date = updateDate;
    
    const response = await api.get<PreviewUpdatesResponse>('/utils/preview-updates', { params });
    return response.data;
  },
};
