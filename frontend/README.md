# Frontend - Graph Duty B24

Frontend приложение для управления графиком дежурств Bitrix24.

## Технологии

- React 18
- TypeScript
- Vite
- Tailwind CSS
- Zustand (state management)
- React Router DOM
- Axios
- date-fns

## Установка

```bash
npm install
```

## Разработка

```bash
npm run dev
```

Приложение будет доступно по адресу `http://localhost:3000`

## Сборка

```bash
npm run build
```

## Переменные окружения

Создайте файл `.env` на основе `.env.example`:

```env
VITE_API_URL=http://localhost:8000
```

## Структура проекта

- `src/pages/` - Страницы приложения
- `src/components/` - React компоненты
- `src/services/` - API клиенты
- `src/store/` - Zustand stores
- `src/types/` - TypeScript типы
- `src/utils/` - Утилиты
