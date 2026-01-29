from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DefaultUserBase(BaseModel):
    user_id: int
    position: int = 0


class DefaultUserCreate(DefaultUserBase):
    pass


class DefaultUserUpdate(BaseModel):
    position: Optional[int] = None


class DefaultUser(DefaultUserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class DefaultUserWithUser(DefaultUser):
    user_name: Optional[str] = None
    user_email: Optional[str] = None


class DefaultUsersReorder(BaseModel):
    """Схема для изменения порядка дефолтных пользователей"""
    user_ids: list[int]  # Список ID пользователей в новом порядке
