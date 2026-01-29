from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.update_history import UpdateSource


class UpdateHistoryBase(BaseModel):
    """Базовая схема истории изменений"""
    entity_type: str
    entity_id: int
    old_assigned_by_id: Optional[int] = None
    new_assigned_by_id: int
    update_source: UpdateSource
    rule_id: Optional[int] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None


class UpdateHistory(UpdateHistoryBase):
    """Схема истории изменений с полными данными"""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class UpdateHistoryWithUsers(UpdateHistory):
    """Схема истории изменений с информацией о пользователях"""
    old_user_name: Optional[str] = None
    new_user_name: Optional[str] = None
    
    class Config:
        from_attributes = True
