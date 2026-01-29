from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.api.routes import api_router
from app.scheduler.tasks import start_scheduler, stop_scheduler
import logging

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Создание таблиц базы данных
Base.metadata.create_all(bind=engine)

# Создание FastAPI приложения
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="1.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if isinstance(settings.cors_origins, list) else [settings.cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    """Событие запуска приложения"""
    logger.info(f"Запуск приложения {settings.app_name}")
    logger.info(f"Режим отладки: {settings.debug}")
    logger.info(f"База данных: {settings.database_url}")
    cors_origins_list = settings.cors_origins if isinstance(settings.cors_origins, list) else [settings.cors_origins]
    logger.info(f"Разрешенные CORS origins: {cors_origins_list}")
    
    # Запускаем планировщик задач
    start_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    """Событие остановки приложения"""
    logger.info("Остановка приложения")
    stop_scheduler()


@app.get("/")
def root():
    """Корневой endpoint"""
    return {
        "message": "Graph Duty B24 API",
        "version": "1.0.0",
        "docs": "/docs"
    }
