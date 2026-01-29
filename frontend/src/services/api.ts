import axios from 'axios';

// В production используем относительный путь /api (проксируется через nginx)
// В development можно указать VITE_API_URL для прямого подключения к бэкенду
const API_URL = import.meta.env.VITE_API_URL || '/api';

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

const TOKEN_KEY = 'auth_token';

// Перехватчик для добавления токена в заголовки
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Перехватчик для обработки ошибок
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Если получили 401, перенаправляем на страницу логина
      // Но не для endpoint логина, чтобы не создавать бесконечный цикл
      const isLoginEndpoint = error.config?.url?.includes('/auth/login');
      if (error.response.status === 401 && !isLoginEndpoint) {
        localStorage.removeItem(TOKEN_KEY);
        // Редирект на страницу логина только если мы не на ней
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
      // Сервер ответил с кодом ошибки
      const message = error.response.data?.detail || error.message;
      return Promise.reject(new Error(message));
    } else if (error.request) {
      // Запрос был сделан, но ответа не получено
      return Promise.reject(new Error('Нет соединения с сервером'));
    } else {
      // Что-то другое
      return Promise.reject(error);
    }
  }
);
