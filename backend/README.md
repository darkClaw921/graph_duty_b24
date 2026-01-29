# Backend Graph Duty B24

Backend приложение для управления графиком дежурств и автоматического обновления ответственных в Bitrix24.

## Описание

Backend реализован на FastAPI и предоставляет REST API для:
- Управления пользователями Bitrix24
- Создания и управления графиком дежурств
- Настройки правил автоматического обновления сущностей
- Автоматического обновления ответственных в Bitrix24 по расписанию

## Требования

- Python >= 3.13
- uv (менеджер пакетов) или pip
- Доступ к Bitrix24 (webhook или OAuth токен)

## Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd graph_duty_b24/backend
```

### 2. Установка зависимостей

С использованием uv (рекомендуется):
```bash
uv sync
```

Или с использованием pip:
```bash
pip install -r requirements.txt
```

### 3. Настройка переменных окружения

Создайте файл `.env` в директории `backend/` на основе `.env.example`:

```bash
cp .env.example .env
```

Отредактируйте `.env` и укажите:
- `BITRIX24_WEBHOOK` - webhook URL вашего Bitrix24 портала
- `BITRIX24_ACCESS_TOKEN` - OAuth токен (альтернатива webhook)
- `DATABASE_URL` - URL базы данных (по умолчанию SQLite)
- `SCHEDULER_ENABLED` - включить/выключить планировщик задач
- `DEFAULT_UPDATE_TIME` - время автоматического обновления (формат HH:MM)
- `CORS_ORIGINS` - разрешенные источники для CORS (через запятую)

### 4. Инициализация базы данных

При первом запуске приложения таблицы создадутся автоматически. Для применения миграций:

```bash
alembic upgrade head
```

## Запуск

### Локальная разработка

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Или с использованием uv:
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker

```bash
docker-compose up backend
```

### Production

Используйте production ASGI сервер (например, gunicorn с uvicorn workers):

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Структура проекта

```
backend/
├── app/                    # Основное приложение
│   ├── main.py            # Точка входа FastAPI
│   ├── config.py          # Конфигурация из переменных окружения
│   ├── database.py        # Настройка SQLAlchemy
│   ├── api/               # API endpoints
│   │   ├── routes.py      # Главный роутер
│   │   ├── users.py       # Управление пользователями
│   │   ├── schedule.py    # Управление графиком
│   │   ├── settings.py    # Настройки (дефолтные пользователи, поля)
│   │   ├── rules.py       # Правила обновления
│   │   └── utils.py       # Утилиты (обновление, health check)
│   ├── models/            # SQLAlchemy модели
│   │   ├── user.py
│   │   ├── duty_schedule.py
│   │   ├── duty_schedule_user.py
│   │   ├── default_users.py
│   │   ├── update_rule.py
│   │   ├── update_rule_user.py
│   │   └── field_mapping.py
│   ├── schemas/           # Pydantic схемы
│   │   ├── user.py
│   │   ├── duty_schedule.py
│   │   ├── default_users.py
│   │   └── update_rule.py
│   ├── services/          # Бизнес-логика
│   │   ├── bitrix_client.py    # Клиент Bitrix24 API
│   │   ├── schedule_service.py # Сервис графика
│   │   ├── update_service.py   # Сервис обновления сущностей
│   │   └── rule_engine.py      # Движок правил
│   ├── scheduler/         # Планировщик задач
│   │   └── tasks.py
│   └── utils/             # Утилиты
├── migrations/            # Миграции Alembic
├── docker/               # Docker файлы
│   └── Dockerfile
├── pyproject.toml        # Зависимости проекта
├── requirements.txt      # Python зависимости
├── alembic.ini           # Конфигурация Alembic
└── .env                  # Переменные окружения (не в git)
```

## API Endpoints

### Пользователи

- `GET /api/users` - Получить список пользователей
- `GET /api/users/{id}` - Получить пользователя по ID
- `PUT /api/users/{id}/toggle-active` - Переключить активность пользователя
- `POST /api/users/sync` - Синхронизировать пользователей с Bitrix24

### График дежурств

- `GET /api/schedule` - Получить график (с фильтрами по датам)
- `POST /api/schedule` - Создать запись в графике
- `PUT /api/schedule/{id}` - Обновить запись
- `DELETE /api/schedule/{id}` - Удалить запись
- `POST /api/schedule/generate` - Сгенерировать график на месяц

### Настройки

- `GET /api/settings/default-users` - Получить дефолтных пользователей
- `POST /api/settings/default-users` - Добавить дефолтного пользователя
- `PUT /api/settings/default-users/{id}` - Обновить позицию дефолтного пользователя
- `DELETE /api/settings/default-users/{id}` - Удалить дефолтного пользователя
- `POST /api/settings/default-users/reorder` - Изменить порядок дефолтных пользователей
- `GET /api/settings/entity-fields` - Получить поля сущностей Bitrix24

### Правила обновления

- `GET /api/rules` - Получить список правил
- `POST /api/rules` - Создать правило
- `GET /api/rules/{id}` - Получить правило по ID
- `PUT /api/rules/{id}` - Обновить правило
- `DELETE /api/rules/{id}` - Удалить правило
- `POST /api/rules/{id}/users` - Добавить пользователей к правилу
- `DELETE /api/rules/{id}/users/{user_id}` - Удалить пользователя из правила

### Утилиты

- `POST /api/utils/update-now` - Принудительное обновление сущностей
- `GET /api/utils/update-count` - Получить количество сущностей для обновления
- `POST /api/utils/update-now-stream` - Обновление с прогрессом (SSE)
- `GET /api/utils/health` - Health check

### Документация API

После запуска приложения доступна интерактивная документация:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Конфигурация

Все настройки приложения загружаются из переменных окружения через `pydantic-settings`.

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `BITRIX24_WEBHOOK` | Webhook URL Bitrix24 | - |
| `BITRIX24_ACCESS_TOKEN` | OAuth токен Bitrix24 | - |
| `APP_NAME` | Название приложения | "Graph Duty B24" |
| `DEBUG` | Режим отладки | False |
| `LOG_LEVEL` | Уровень логирования | INFO |
| `DATABASE_URL` | URL базы данных | sqlite:///./data/graph_duty.db |
| `SCHEDULER_ENABLED` | Включить планировщик | True |
| `DEFAULT_UPDATE_TIME` | Время обновления (HH:MM) | 09:00 |
| `CORS_ORIGINS` | Разрешенные источники CORS | http://localhost:3000,http://localhost:5173 |

## База данных

Приложение использует SQLAlchemy ORM для работы с базой данных. По умолчанию используется SQLite, но можно настроить PostgreSQL или другую БД через `DATABASE_URL`.

### Миграции

Миграции управляются через Alembic:

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "описание изменений"

# Применить миграции
alembic upgrade head

# Откатить миграцию
alembic downgrade -1
```

## Планировщик задач

Приложение использует APScheduler для автоматического выполнения задач. По умолчанию настроено ежедневное обновление ответственных в сущностях Bitrix24 в указанное время.

Планировщик можно отключить через переменную окружения `SCHEDULER_ENABLED=False`.

## Разработка

### Установка зависимостей для разработки

```bash
uv sync --dev
```

### Запуск тестов

```bash
pytest
```

### Форматирование кода

```bash
black app/
isort app/
```

### Линтинг

```bash
ruff check app/
```

## Зависимости

Основные зависимости:
- `fastapi` - веб-фреймворк
- `fast-bitrix24` - клиент Bitrix24 REST API
- `sqlalchemy` - ORM для работы с БД
- `alembic` - миграции БД
- `apscheduler` - планировщик задач
- `pydantic` - валидация данных
- `uvicorn` - ASGI сервер

Полный список зависимостей см. в `pyproject.toml` или `requirements.txt`.

## Логирование

Логирование настраивается через переменную окружения `LOG_LEVEL`. Доступные уровни:
- DEBUG
- INFO
- WARNING
- ERROR
- CRITICAL

## Troubleshooting

### Проблемы с подключением к Bitrix24

1. Проверьте правильность webhook URL или токена
2. Убедитесь, что у пользователя есть права на необходимые методы API
3. Проверьте логи приложения на наличие ошибок

### Проблемы с базой данных

1. Убедитесь, что директория `data/` существует и доступна для записи
2. Проверьте права доступа к файлу базы данных
3. При использовании PostgreSQL проверьте подключение и права пользователя

### Проблемы с планировщиком

1. Проверьте переменную `SCHEDULER_ENABLED`
2. Убедитесь, что время указано в правильном формате (HH:MM)
3. Проверьте логи на наличие ошибок при выполнении задач

## Лицензия

[Указать лицензию проекта]
Обновление сущностей...
