from fastapi import APIRouter, HTTPException, status
from datetime import timedelta
from app.schemas.auth import LoginRequest, LoginResponse
from app.config import settings
from app.auth.security import verify_password, create_access_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """Авторизация пользователя"""
    # Нормализуем данные (убираем пробелы)
    username = login_data.username.strip() if login_data.username else ""
    password = login_data.password.strip() if login_data.password else ""
    admin_username = settings.admin_username.strip() if settings.admin_username else ""
    admin_password = settings.admin_password.strip() if settings.admin_password else ""
    
    #logger.debug(f"Попытка входа: username='{username}', admin_username='{admin_username}'")
    
    # Проверяем логин и пароль с данными из .env
    if username != admin_username or password != admin_password:
        logger.warning(f"Неудачная попытка входа: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Создаем токен
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": login_data.username}, expires_delta=access_token_expires
    )
    
    logger.info(f"Успешная авторизация: {login_data.username}")
    
    return LoginResponse(access_token=access_token, token_type="bearer")
