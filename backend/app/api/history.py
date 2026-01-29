from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import date, datetime
from app.database import get_db
from app.models import UpdateHistory, User
from app.schemas.update_history import UpdateHistoryWithUsers
from app.auth.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=List[UpdateHistoryWithUsers])
def get_update_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    entity_type: Optional[str] = Query(None, description="Тип сущности (deal, contact, company)"),
    entity_id: Optional[int] = Query(None, description="ID сущности"),
    start_date: Optional[date] = Query(None, description="Начальная дата"),
    end_date: Optional[date] = Query(None, description="Конечная дата"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Получить историю изменений ответственных в сущностях
    
    Поддерживает фильтрацию по типу сущности, ID сущности и датам
    """
    try:
        query = db.query(UpdateHistory)
        
        # Применяем фильтры
        if entity_type:
            query = query.filter(UpdateHistory.entity_type == entity_type)
        
        if entity_id:
            query = query.filter(UpdateHistory.entity_id == entity_id)
        
        if start_date:
            query = query.filter(UpdateHistory.created_at >= datetime.combine(start_date, datetime.min.time()))
        
        if end_date:
            query = query.filter(UpdateHistory.created_at <= datetime.combine(end_date, datetime.max.time()))
        
        # Сортируем по дате создания (новые сначала)
        query = query.order_by(desc(UpdateHistory.created_at))
        
        # Применяем пагинацию
        history_items = query.offset(skip).limit(limit).all()
        
        # Получаем информацию о пользователях
        result = []
        for item in history_items:
            history_dict = {
                "id": item.id,
                "entity_type": item.entity_type,
                "entity_id": item.entity_id,
                "old_assigned_by_id": item.old_assigned_by_id,
                "new_assigned_by_id": item.new_assigned_by_id,
                "update_source": item.update_source,
                "rule_id": item.rule_id,
                "related_entity_type": item.related_entity_type,
                "related_entity_id": item.related_entity_id,
                "created_at": item.created_at,
                "old_user_name": None,
                "new_user_name": None
            }
            
            # Получаем имя старого пользователя
            if item.old_assigned_by_id:
                old_user = db.query(User).filter(User.id == item.old_assigned_by_id).first()
                if old_user:
                    history_dict["old_user_name"] = f"{old_user.name or ''} {old_user.last_name or ''}".strip()
            
            # Получаем имя нового пользователя
            if item.new_assigned_by_id:
                new_user = db.query(User).filter(User.id == item.new_assigned_by_id).first()
                if new_user:
                    history_dict["new_user_name"] = f"{new_user.name or ''} {new_user.last_name or ''}".strip()
            
            result.append(UpdateHistoryWithUsers(**history_dict))
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении истории изменений: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении истории: {str(e)}")


@router.get("/count")
def get_update_history_count(
    entity_type: Optional[str] = Query(None, description="Тип сущности (deal, contact, company)"),
    entity_id: Optional[int] = Query(None, description="ID сущности"),
    start_date: Optional[date] = Query(None, description="Начальная дата"),
    end_date: Optional[date] = Query(None, description="Конечная дата"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Получить количество записей в истории изменений с учетом фильтров
    """
    try:
        query = db.query(UpdateHistory)
        
        # Применяем фильтры
        if entity_type:
            query = query.filter(UpdateHistory.entity_type == entity_type)
        
        if entity_id:
            query = query.filter(UpdateHistory.entity_id == entity_id)
        
        if start_date:
            query = query.filter(UpdateHistory.created_at >= datetime.combine(start_date, datetime.min.time()))
        
        if end_date:
            query = query.filter(UpdateHistory.created_at <= datetime.combine(end_date, datetime.max.time()))
        
        count = query.count()
        return {"count": count}
    except Exception as e:
        logger.error(f"Ошибка при подсчете истории изменений: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при подсчете истории: {str(e)}")
