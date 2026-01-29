from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List, Union
import secrets


class Settings(BaseSettings):
    """Конфигурация приложения из переменных окружения"""
    
    # Bitrix24
    bitrix24_webhook: Optional[str] = None
    bitrix24_access_token: Optional[str] = None
    
    # Приложение
    app_name: str = "Graph Duty B24"
    debug: bool = False
    log_level: str = "INFO"
    
    # База данных
    database_url: str = "sqlite:///./data/graph_duty.db"
    
    # Планировщик
    scheduler_enabled: bool = True
    default_update_time: str = "09:00"
    
    # CORS
    cors_origins: Union[str, List[str]] = "http://localhost:3000,http://localhost:5173"
    
    # Webhook
    webhook_base_url: Optional[str] = None  # Базовый URL для генерации webhook URL (например, https://yourdomain.com)
    
    # Авторизация
    admin_username: str = "admin"
    admin_password: str = "admin"
    secret_key: str = secrets.token_urlsafe(32)  # Генерируется случайно, если не указан в .env
    access_token_expire_minutes: int = 1440  # 24 часа
    
    @field_validator('cors_origins')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
