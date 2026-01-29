from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User
from app.schemas.user import User as UserSchema
from app.services.bitrix_client import get_bitrix_client
from app.auth.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=List[UserSchema])
def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить список всех пользователей"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserSchema)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить пользователя по ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@router.put("/{user_id}/toggle-active", response_model=UserSchema)
def toggle_user_active(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Переключить статус активности пользователя"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    user.active = not user.active
    db.commit()
    db.refresh(user)
    
    logger.info(f"Статус пользователя {user_id} изменен на {'активен' if user.active else 'неактивен'}")
    return user


def _parse_active_status(active_value) -> bool:
    """Преобразовать значение ACTIVE из Bitrix24 в булево значение"""
    if isinstance(active_value, bool):
        return active_value
    if isinstance(active_value, str):
        return active_value.upper() == 'Y'
    return False


@router.post("/sync")
async def sync_users(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Принудительная синхронизация пользователей с Bitrix24"""
    try:
        bitrix_client = get_bitrix_client()
        bitrix_users = await bitrix_client.get_all_users()
        
        updated_count = 0
        created_count = 0
        
        for bitrix_user in bitrix_users:
            user_id = int(bitrix_user.get('ID'))
            existing_user = db.query(User).filter(User.id == user_id).first()
            
            active_status = _parse_active_status(bitrix_user.get('ACTIVE'))
            
            if existing_user:
                # Обновляем существующего пользователя
                existing_user.name = bitrix_user.get('NAME')
                existing_user.last_name = bitrix_user.get('LAST_NAME')
                existing_user.email = bitrix_user.get('EMAIL')
                existing_user.active = active_status
                updated_count += 1
            else:
                # Создаем нового пользователя
                new_user = User(
                    id=user_id,
                    name=bitrix_user.get('NAME'),
                    last_name=bitrix_user.get('LAST_NAME'),
                    email=bitrix_user.get('EMAIL'),
                    active=active_status
                )
                db.add(new_user)
                created_count += 1
        
        db.commit()
        
        logger.info(f"Синхронизировано пользователей: создано {created_count}, обновлено {updated_count}")
        
        return {
            "message": "Синхронизация завершена",
            "created": created_count,
            "updated": updated_count,
            "total": len(bitrix_users)
        }
    except Exception as e:
        logger.error(f"Ошибка при синхронизации пользователей: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка синхронизации: {str(e)}")
