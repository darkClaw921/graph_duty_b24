from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional, Dict
from datetime import date, datetime
from zoneinfo import ZoneInfo
from app.database import get_db
from app.models import UpdateHistory, User, UpdateSource
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
    update_source: Optional[UpdateSource] = Query(None, description="Источник обновления (webhook, scheduled, manual)"),
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
        
        if update_source:
            query = query.filter(UpdateHistory.update_source == update_source)
        
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
    update_source: Optional[UpdateSource] = Query(None, description="Источник обновления (webhook, scheduled, manual)"),
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
        
        if update_source:
            query = query.filter(UpdateHistory.update_source == update_source)
        
        count = query.count()
        return {"count": count}
    except Exception as e:
        logger.error(f"Ошибка при подсчете истории изменений: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при подсчете истории: {str(e)}")


@router.get("/stats/{stats_date}/{user_id}")
def get_user_entity_stats(
    stats_date: date,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Получить статистику по сущностям для пользователя на указанную дату
    
    Returns:
        Словарь {entity_type: count} где entity_type - тип сущности (deal, contact, company, lead),
        count - количество сущностей, назначенных на пользователя в этот день
    """
    try:
        # Определяем начало и конец дня для указанной даты в московском часовом поясе
        MSK_TIMEZONE = ZoneInfo("Europe/Moscow")
        start_datetime = datetime.combine(stats_date, datetime.min.time(), tzinfo=MSK_TIMEZONE)
        end_datetime = datetime.combine(stats_date, datetime.max.time(), tzinfo=MSK_TIMEZONE)
        
        # Запрос к UpdateHistory: группируем по типу сущности
        stats_query = db.query(
            UpdateHistory.entity_type,
            func.count(UpdateHistory.id).label('count')
        ).filter(
            UpdateHistory.new_assigned_by_id == user_id,
            UpdateHistory.created_at >= start_datetime,
            UpdateHistory.created_at <= end_datetime
        ).group_by(UpdateHistory.entity_type)
        
        # Получаем результаты и формируем словарь
        stats_result = stats_query.all()
        stats_dict: Dict[str, int] = {}
        
        for entity_type, count in stats_result:
            if entity_type:
                stats_dict[entity_type] = count
        
        return stats_dict
    except Exception as e:
        logger.error(f"Ошибка при получении статистики для пользователя {user_id} на дату {stats_date}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики: {str(e)}")
