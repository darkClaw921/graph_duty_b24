# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Копирование package файлов
COPY package*.json ./

# Установка зависимостей
RUN npm ci

# Копирование исходного кода
COPY . .

# Сборка приложения
RUN npm run build

# Stage 2: Production
FROM nginx:alpine

# Копирование собранного приложения
COPY --from=builder /app/dist /usr/share/nginx/html

# Копирование конфигурации nginx
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# Порт nginx
EXPOSE 80

# Запуск nginx
CMD ["nginx", "-g", "daemon off;"]
