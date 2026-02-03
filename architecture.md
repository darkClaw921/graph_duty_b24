# Архитектура проекта Graph Duty B24

## Структура проекта

```
graph_duty_b24/
├── backend/                    # Backend на FastAPI
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # Точка входа FastAPI приложения, настройка CORS, подключение роутеров
│   │   ├── config.py           # Конфигурация приложения (загрузка переменных окружения через pydantic-settings)
│   │   ├── database.py         # Подключение к SQLite через SQLAlchemy, создание сессий, Base для моделей
│   │   ├── auth/               # Модуль авторизации
│   │   │   ├── __init__.py     # Экспорт зависимостей авторизации
│   │   │   ├── dependencies.py # Dependency get_current_user для проверки JWT токена в заголовках запросов
│   │   │   └── security.py     # Функции для создания/проверки JWT токенов, хеширования/проверки паролей
│   │   ├── models/             # SQLAlchemy модели базы данных
│   │   │   ├── __init__.py     # Экспорт всех моделей
│   │   │   ├── user.py         # Модель пользователя Bitrix24 (id, name, last_name, email, active)
│   │   │   ├── duty_schedule.py # Модель графика дежурств (id, date)
│   │   │   ├── duty_schedule_user.py # Промежуточная таблица для связи многие-ко-многим между графиком и пользователями (duty_schedule_id, user_id)
│   │   │   ├── default_users.py # Дефолтные пользователи для графика (id, user_id, position)
│   │   │   ├── update_rule.py  # Правила обновления сущностей (entity_type, entity_name, rule_type, condition_config, priority, update_time, update_days, distribution_percentage)
│   │   │   ├── update_rule_user.py # Промежуточная таблица для связи многие-ко-многим между правилами и пользователями (update_rule_id, user_id)
│   │   │   ├── update_history.py # История изменений ответственных в сущностях (entity_type, entity_id, old_assigned_by_id, new_assigned_by_id, update_source, rule_id, related_entity_type, related_entity_id)
│   │   │   └── field_mapping.py # Маппинг полей Bitrix24 (entity_type, field_id, field_name, field_type)
│   │   ├── schemas/            # Pydantic схемы для валидации данных API
│   │   │   ├── __init__.py
│   │   │   ├── user.py         # Схемы User, UserCreate, UserUpdate
│   │   │   ├── duty_schedule.py # Схемы DutySchedule, DutyScheduleCreate, DutyScheduleUpdate, DutyScheduleWithUser
│   │   │   ├── update_rule.py  # Схемы UpdateRule, UpdateRuleCreate, UpdateRuleUpdate
│   │   │   ├── update_history.py # Схемы UpdateHistory, UpdateHistoryWithUsers
│   │   │   ├── default_users.py # Схемы DefaultUser, DefaultUserCreate, DefaultUsersReorder
│   │   │   └── auth.py         # Схемы LoginRequest, LoginResponse для авторизации
│   │   ├── api/                # API endpoints FastAPI
│   │   │   ├── __init__.py
│   │   │   ├── routes.py       # Главный роутер, объединяющий все endpoints
│   │   │   ├── auth.py         # Endpoint авторизации (POST /api/auth/login) - проверка логина/пароля из .env, выдача JWT токена
│   │   │   ├── users.py        # Endpoints для управления пользователями (GET /api/users, GET /api/users/{id}, PUT /api/users/{id}/toggle-active, POST /api/users/sync) - защищены авторизацией
│   │   │   ├── schedule.py     # Endpoints для управления графиком (GET/POST/PUT/DELETE /api/schedule, POST /api/schedule/generate) - защищены авторизацией
│   │   │   ├── settings.py     # Endpoints для настроек (дефолтные пользователи, поля сущностей) - защищены авторизацией
│   │   │   ├── rules.py        # Endpoints для правил обновления (CRUD операции, управление пользователями правил) - защищены авторизацией
│   │   │   ├── utils.py        # Утилитарные endpoints (POST /api/utils/update-now, GET /api/utils/update-count, POST /api/utils/update-now-stream, GET /api/utils/preview-updates, GET /api/utils/health) - защищены авторизацией
│   │   │   ├── webhook.py      # Обработчик webhook событий от Bitrix24 (POST /api/webhook/bitrix). При обновлении сделки распределяет ответственного между пользователями на дежурстве по очереди на основе deal_id. Не защищен авторизацией (вызывается извне)
│   │   │   └── history.py      # Endpoints для получения истории изменений (GET /api/history, GET /api/history/count) с фильтрацией по типу сущности, ID, датам - защищены авторизацией
│   │   ├── services/           # Бизнес-логика приложения
│   │   │   ├── __init__.py
│   │   │   ├── bitrix_client.py # Клиент для работы с Bitrix24 REST API через библиотеку fast_bitrix24
│   │   │   │                    # Методы: get_all_users, get_entity_fields, get_entities_list, update_entities_batch
│   │   │   ├── schedule_service.py # Сервис графика дежурств (генерация, получение, создание/обновление записей)
│   │   │   ├── update_service.py # Сервис обновления сущностей (применение правил, обновление через Bitrix24 API, получение количества сущностей для обновления, обновление с прогрессом через генератор, предпросмотр обновляемых сущностей)
│   │   │   └── rule_engine.py  # Движок выполнения правил для фильтрации сущностей по условиям (поддержка множественного выбора воронок через category_ids)
│   │   ├── scheduler/          # Планировщик задач
│   │   │   ├── __init__.py
│   │   │   └── tasks.py        # Задачи для APScheduler (ежедневное обновление ответственных)
│   │   └── utils/              # Утилиты
│   │       ├── __init__.py
│   │       └── validators.py   # Валидаторы данных (если потребуется)
│   ├── migrations/             # Миграции базы данных (Alembic)
│   │   ├── versions/           # Файлы миграций
│   │   └── env.py              # Конфигурация Alembic
│   ├── tests/                  # Тесты backend
│   ├── docker/
│   │   └── Dockerfile          # Docker образ backend (Python 3.11-slim, установка зависимостей, запуск uvicorn)
│   ├── requirements.txt        # Python зависимости
│   ├── alembic.ini             # Конфигурация Alembic
│   └── .env.example            # Пример переменных окружения backend
│
├── frontend/                   # Frontend на React + TypeScript
│   ├── public/                 # Статические файлы
│   │   └── index.html          # HTML шаблон
│   ├── src/
│   │   ├── components/         # React компоненты
│   │   │   ├── common/         # Общие компоненты (Button, Input, Modal)
│   │   │   ├── layout/         # Компоненты layout (Layout, Header)
│   │   │   ├── schedule/       # Компоненты графика дежурств (если потребуется)
│   │   │   ├── users/          # Компоненты пользователей (если потребуется)
│   │   │   └── settings/       # Компоненты настроек (DefaultUsersSettings, EntityConfigSettings, UpdateRulesSettings)
│   │   ├── pages/              # Страницы приложения
│   │   │   ├── Dashboard.tsx   # Главная страница со статистикой
│   │   │   ├── Schedule.tsx    # Страница графика дежурств с календарем, кнопкой принудительного обновления сущностей, кнопкой предпросмотра обновлений и прогресс баром
│   │   │   ├── Users.tsx       # Страница пользователей с синхронизацией
│   │   │   ├── Settings.tsx    # Страница настроек
│   │   │   └── History.tsx     # Страница истории изменений ответственных с фильтрацией и пагинацией
│   │   ├── services/           # API клиенты
│   │   │   ├── api.ts          # Базовый API клиент (axios)
│   │   │   ├── usersApi.ts     # API для пользователей
│   │   │   ├── scheduleApi.ts  # API для графика
│   │   │   ├── settingsApi.ts  # API для настроек
│   │   │   ├── rulesApi.ts     # API для правил
│   │   │   ├── historyApi.ts   # API для истории изменений
│   │   │   └── utilsApi.ts    # API для утилит (получение количества сущностей для обновления, обновление с прогрессом через streaming, предпросмотр обновляемых сущностей)
│   │   ├── store/              # Zustand stores для state management
│   │   │   ├── scheduleStore.ts # Store для графика дежурств
│   │   │   ├── usersStore.ts   # Store для пользователей
│   │   │   └── settingsStore.ts # Store для настроек
│   │   ├── types/              # TypeScript типы
│   │   │   ├── user.ts         # Типы пользователей
│   │   │   ├── schedule.ts     # Типы графика дежурств
│   │   │   ├── entity.ts       # Типы сущностей
│   │   │   ├── rule.ts         # Типы правил
│   │   │   ├── history.ts      # Типы истории изменений (UpdateHistory, UpdateHistoryFilters, UpdateSource)
│   │   │   └── defaultUsers.ts # Типы дефолтных пользователей
│   │   ├── utils/              # Утилиты
│   │   │   └── dateUtils.ts    # Утилиты для работы с датами
│   │   ├── App.tsx             # Главный компонент приложения с роутингом
│   │   ├── main.tsx            # Точка входа React
│   │   └── index.css           # Глобальные стили (Tailwind CSS)
│   ├── docker/
│   │   ├── Dockerfile          # Docker образ frontend (multi-stage: сборка через Node.js + nginx для статики)
│   │   └── nginx.conf          # Конфигурация nginx (SPA routing, проксирование API на backend)
│   ├── package.json            # npm зависимости и скрипты
│   ├── tsconfig.json           # TypeScript конфигурация
│   ├── vite.config.ts          # Vite конфигурация
│   ├── tailwind.config.js      # Tailwind CSS конфигурация
│   ├── postcss.config.js       # PostCSS конфигурация
│   └── .gitignore              # Git ignore правила
│
├── docker-compose.yml          # Docker Compose конфигурация для всех сервисов (backend на порту 8000, frontend на порту 3000, сеть graph_duty_network, healthcheck для backend)
└── architecture.md             # Этот файл - описание архитектуры проекта
```

## Описание компонентов

### Backend (FastAPI)

#### main.py
Точка входа приложения. Настраивает FastAPI, CORS middleware, подключает роутеры, запускает планировщик задач при старте.

#### config.py
Загружает переменные окружения через pydantic-settings. Содержит настройки Bitrix24, базы данных, планировщика, CORS, авторизации (admin_username, admin_password, secret_key, access_token_expire_minutes).

#### database.py
Настраивает SQLAlchemy engine и сессии. Создает Base для моделей. Предоставляет dependency `get_db()` для FastAPI endpoints.

#### Модели (models/)
SQLAlchemy ORM модели для работы с базой данных:
- **User**: Пользователи Bitrix24
- **DefaultUser**: Дефолтные пользователи для генерации графика
- **DutySchedule**: График дежурств (дата)
- **DutyScheduleUser**: Промежуточная таблица для связи многие-ко-многим между графиком и пользователями (позволяет нескольким пользователям работать в один день)
- **UpdateRule**: Правила обновления сущностей (тип сущности, название, тип правила, условия фильтрации, приоритет, время обновления, дни недели, процент распределения)
- **UpdateRuleUser**: Промежуточная таблица для связи многие-ко-многим между правилами и пользователями (правило применяется только когда пользователи из правила на дежурстве)
- **UpdateHistory**: История изменений ответственных в сущностях (тип сущности, ID сущности, старый и новый ответственный, источник обновления, правило, связанная сущность)
- **FieldMapping**: Кэш полей сущностей Bitrix24

#### Схемы (schemas/)
Pydantic схемы для валидации и сериализации данных в API endpoints:
- **auth.py**: LoginRequest (username, password), LoginResponse (access_token, token_type)

#### API Endpoints (api/)
REST API endpoints для управления графиком, пользователями, настройками и правилами:
- **auth.py**: Endpoint авторизации (POST /api/auth/login) - проверяет логин и пароль с данными из .env, возвращает JWT токен. Не защищен авторизацией.
- **webhook.py**: Обработчик webhook событий от Bitrix24 (POST /api/webhook/bitrix). При обновлении сделки через webhook сначала проверяет текущего ответственного за сделку. Если ответственный уже есть в графике дежурств на текущий день, обновление не выполняется, но запись об этом записывается в UpdateHistory (с одинаковыми old_assigned_by_id и new_assigned_by_id). Если ответственного нет в графике, распределяет ответственного между пользователями на дежурстве поочередно на основе последнего обновленного пользователя из UpdateHistory. Если несколько пользователей в графике на день, при каждом обновлении выбирается следующий пользователь по кругу из списка дежурных. Если последнего пользователя нет в текущем графике или это первое обновление, выбирается первый пользователь из списка. Если правило имеет флаг update_related_contacts_companies=True, также обновляются ответственные в связанных контактах и компании сделки. Не защищен авторизацией (вызывается извне).
- Все остальные endpoints защищены dependency get_current_user, который проверяет JWT токен в заголовке Authorization.

#### Сервисы (services/)
Бизнес-логика приложения:
- **bitrix_client.py**: Обертка над библиотекой fast_bitrix24 для работы с Bitrix24 REST API
- **schedule_service.py**: Логика работы с графиком дежурств (генерация, CRUD операции, поддержка нескольких пользователей на дату)
- **update_service.py**: Логика обновления ответственных в сущностях Bitrix24 с применением правил и процентным распределением между пользователями. Правила применяются только когда пользователи из правила находятся на дежурстве. При обновлении по планировщику система всегда перераспределяет все сущности по правилам распределения, даже если ответственный уже правильный, чтобы обеспечить равномерное распределение нагрузки. Записывает историю изменений в UpdateHistory для всех обновлений, включая связанные сущности (контакты и компании). Поддерживает предпросмотр обновляемых сущностей без реального обновления через метод get_preview_updates.
- **rule_engine.py**: Движок правил для фильтрации сущностей по условиям (assigned_by_condition, field_condition, combined). Поддерживает множественный выбор воронок через массив category_ids в condition_config (обратная совместимость с category_id сохранена)

#### Модуль авторизации (auth/)
Модуль для работы с авторизацией пользователей:
- **dependencies.py**: Dependency `get_current_user()` для проверки JWT токена в заголовках запросов. Используется во всех защищенных endpoints.
- **security.py**: Функции для создания/проверки JWT токенов (create_access_token, verify_token), хеширования/проверки паролей (get_password_hash, verify_password).

#### Планировщик (scheduler/)
APScheduler задачи для автоматического ежедневного обновления ответственных в указанное время.

### Frontend (React + TypeScript)

#### App.tsx
Главный компонент приложения с настройкой роутинга через react-router-dom. Определяет маршруты для всех страниц. Защищает все маршруты кроме /login компонентом ProtectedRoute, который проверяет авторизацию и перенаправляет на /login если пользователь не авторизован.

#### Страницы (pages/)
- **Login.tsx**: Страница авторизации с формой логина и пароля, валидацией полей, обработкой ошибок авторизации
- **Dashboard.tsx**: Главная страница с общей статистикой (количество пользователей, дежурств, дежурный сегодня, ближайшие дежурства) - защищена авторизацией
- **Schedule.tsx**: Страница графика дежурств с табличным видом (пользователи в строках, даты в столбцах), отображением количества отработанных дней для каждого пользователя, возможностью создания/редактирования/удаления записей через клик по ячейке и генерации графика на месяц - защищена авторизацией
- **Users.tsx**: Страница пользователей с отображением списка, поиском и синхронизацией с Bitrix24 - защищена авторизацией
- **Settings.tsx**: Страница настроек с табами для управления дефолтными пользователями и правилами обновления сущностей - защищена авторизацией
- **History.tsx**: Страница истории изменений ответственных с фильтрацией и пагинацией - защищена авторизацией

#### Компоненты (components/)
- **common/**: Переиспользуемые компоненты (Button, Input, Modal, PreviewUpdatesModal, ProtectedRoute)
- **layout/**: Компоненты структуры страницы (Layout с сайдбаром, Header с кнопкой выхода)
- **settings/**: Компоненты настроек (DefaultUsersSettings, UpdateRulesSettings)

#### API клиенты (services/)
Обертки над axios для работы с backend API:
- **api.ts**: Базовый клиент с настройкой interceptors для автоматического добавления JWT токена в заголовок Authorization и обработки ошибок (редирект на /login при 401)
- **authApi.ts**: Методы для авторизации (login)
- **usersApi.ts**: Методы для работы с пользователями
- **scheduleApi.ts**: Методы для работы с графиком дежурств
- **settingsApi.ts**: Методы для работы с настройками (дефолтные пользователи, поля сущностей)
- **rulesApi.ts**: Методы для работы с правилами обновления
- **historyApi.ts**: Методы для работы с историей изменений
- **utilsApi.ts**: Методы для утилит (обновление сущностей, предпросмотр)

#### Stores (store/)
Zustand stores для управления состоянием приложения:
- **authStore.ts**: Состояние авторизации (токен, isAuthenticated, методы login, logout, checkAuth). Сохраняет токен в localStorage.
- **scheduleStore.ts**: Состояние графика дежурств (список, загрузка, ошибки, методы CRUD и генерации)
- **usersStore.ts**: Состояние пользователей (список, загрузка, синхронизация)
- **settingsStore.ts**: Состояние настроек (дефолтные пользователи, методы CRUD)

#### Типы (types/)
TypeScript интерфейсы для типизации данных:
- **auth.ts**: LoginRequest, LoginResponse, User
- **user.ts**: User, UserCreate
- **schedule.ts**: DutySchedule, DutyScheduleWithUser, DutyScheduleCreate, DutyScheduleUpdate
- **entity.ts**: EntityField
- **rule.ts**: UpdateRule, UpdateRuleCreate, UpdateRuleUpdate (с полями entity_type, entity_name, update_time, update_days, distribution_percentage, user_ids). condition_config поддерживает category_ids (массив воронок) для множественного выбора воронок в правилах
- **defaultUsers.ts**: DefaultUser, DefaultUserWithUser, DefaultUserCreate, DefaultUsersReorder
- **history.ts**: UpdateHistory, UpdateHistoryWithUsers

#### Утилиты (utils/)
- **dateUtils.ts**: Функции форматирования дат с использованием date-fns и локали ru

## Поток данных

1. **Авторизация**: POST /api/auth/login -> проверка логина/пароля с данными из .env -> создание JWT токена -> возврат токена клиенту -> сохранение токена в localStorage на frontend
2. **Защищенные запросы**: Frontend добавляет токен в заголовок Authorization: Bearer <token> -> Backend проверяет токен через get_current_user dependency -> если токен валиден, запрос выполняется, иначе возвращается 401 -> Frontend перехватывает 401 и перенаправляет на /login
3. **Синхронизация пользователей**: API endpoint `/api/users/sync` -> Bitrix24 API -> сохранение в БД
4. **Генерация графика**: API endpoint `/api/schedule/generate` -> дефолтные пользователи -> создание записей в БД
5. **Ежедневное обновление**: Планировщик -> проверка правил (время/дни) -> получение пользователей на дежурстве -> фильтрация правил по пользователям на дежурстве -> получение сущностей из Bitrix24 -> применение правил фильтрации -> распределение между пользователями из правила -> обновление через Bitrix24 API
6. **Принудительное обновление**: API endpoint `/api/utils/update-now` -> та же логика что и ежедневное обновление
7. **Принудительное обновление с прогрессом**: API endpoint `/api/utils/update-now-stream` -> обновление с отправкой прогресса через Server-Sent Events (SSE), endpoint `/api/utils/update-count` -> получение количества сущностей для обновления без реального обновления
8. **Предпросмотр обновляемых сущностей**: API endpoint `/api/utils/preview-updates` -> получение списка сущностей которые будут обновлены без реального обновления -> отображение в модальном окне с фильтрацией по типу сущности и правилу, показ связанных сущностей (контакты/компании)
9. **Обновление через webhook**: Webhook событие от Bitrix24 (OnCrmDealAdd/OnCrmDealUpdate) -> POST /api/webhook/bitrix -> получение пользователей на дежурстве -> проверка применимости правил -> фильтрация сделки по правилам -> проверка текущего ответственного за сделку: если ответственный уже есть в графике дежурств, запись в UpdateHistory (без обновления в Bitrix24) и завершение обработки; если ответственного нет в графике -> получение последнего обновленного пользователя из UpdateHistory для этой сделки -> выбор следующего пользователя по кругу из списка дежурных (если последнего пользователя нет в графике или это первое обновление, выбирается первый) -> обновление ответственного в сделке через Bitrix24 API -> если правило имеет update_related_contacts_companies=True, получение связанных контактов и компании -> обновление ответственных в связанных контактах и компании -> запись истории изменения в UpdateHistory для сделки и связанных сущностей
10. **Просмотр истории изменений**: GET /api/history -> фильтрация по типу сущности, ID, датам -> возврат истории с информацией о старом и новом ответственном, источнике обновления, связанных сущностях

## Поток данных Frontend

1. **Авторизация**: Пользователь вводит логин/пароль на странице Login -> authStore.login() -> authApi.login() -> сохранение токена в localStorage -> редирект на главную страницу
2. **Защита роутов**: При переходе на защищенный роут -> ProtectedRoute проверяет isAuthenticated из authStore -> если не авторизован, редирект на /login
3. **API запросы**: Все запросы через api.ts автоматически добавляют токен из localStorage в заголовок Authorization -> при получении 401 токен удаляется из localStorage и происходит редирект на /login
4. **Загрузка данных**: Компоненты используют Zustand stores -> API клиенты -> Backend API -> обновление состояния в stores
5. **Создание/обновление**: Пользователь заполняет форму -> вызов метода store -> API клиент -> Backend API -> обновление локального состояния
6. **Синхронизация**: Кнопка синхронизации -> usersStore.syncUsers() -> API синхронизации -> обновление списка пользователей
7. **Выход**: Кнопка выхода в Header -> authStore.logout() -> удаление токена из localStorage -> редирект на /login

## Зависимости

### Backend
- **fastapi**: Веб-фреймворк для REST API
- **fast_bitrix24**: Библиотека для работы с Bitrix24 REST API (автоматическая обработка rate limits, batch операции)
- **sqlalchemy**: ORM для работы с базой данных
- **alembic**: Миграции базы данных
- **apscheduler**: Планировщик задач для автоматического обновления
- **pydantic**: Валидация данных
- **uvicorn**: ASGI сервер для запуска FastAPI
- **python-jose**: Работа с JWT токенами
- **passlib**: Хеширование паролей

### Frontend
- **react**: UI библиотека
- **react-dom**: React для DOM
- **react-router-dom**: Маршрутизация
- **typescript**: Типизация
- **vite**: Сборщик и dev сервер
- **axios**: HTTP клиент для API запросов
- **zustand**: State management
- **tailwindcss**: Utility-first CSS framework
- **date-fns**: Работа с датами
