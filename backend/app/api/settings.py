from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models import DefaultUser, User, FieldMapping, UpdateRule
from app.schemas.default_users import (
    DefaultUser as DefaultUserSchema,
    DefaultUserCreate,
    DefaultUserUpdate,
    DefaultUsersReorder,
    DefaultUserWithUser
)
from app.services.bitrix_client import get_bitrix_client
from app.config import settings
from app.auth.dependencies import get_current_user
import json

router = APIRouter(prefix="/api/settings", tags=["settings"])


# Дефолтные пользователи
@router.get("/default-users", response_model=List[DefaultUserWithUser])
def get_default_users(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить список дефолтных пользователей"""
    default_users = db.query(DefaultUser).join(User).filter(
        User.active == True
    ).order_by(DefaultUser.position).all()
    
    result = []
    for du in default_users:
        user = db.query(User).filter(User.id == du.user_id).first()
        du_dict = DefaultUserWithUser.model_validate(du)
        if user:
            du_dict.user_name = f"{user.name or ''} {user.last_name or ''}".strip()
            du_dict.user_email = user.email
        result.append(du_dict)
    
    return result


@router.post("/default-users", response_model=DefaultUserSchema)
def create_default_user(
    data: DefaultUserCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Добавить дефолтного пользователя"""
    # Проверяем, существует ли пользователь
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Проверяем, не добавлен ли уже
    existing = db.query(DefaultUser).filter(DefaultUser.user_id == data.user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Пользователь уже в списке дефолтных")
    
    # Определяем максимальную позицию
    max_position = db.query(DefaultUser).order_by(DefaultUser.position.desc()).first()
    position = (max_position.position + 1) if max_position else 0
    
    default_user = DefaultUser(
        user_id=data.user_id,
        position=position
    )
    db.add(default_user)
    db.commit()
    db.refresh(default_user)
    return default_user


@router.delete("/default-users/{default_user_id}")
def delete_default_user(
    default_user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Удалить дефолтного пользователя"""
    default_user = db.query(DefaultUser).filter(DefaultUser.id == default_user_id).first()
    if not default_user:
        raise HTTPException(status_code=404, detail="Дефолтный пользователь не найден")
    
    db.delete(default_user)
    db.commit()
    return {"message": "Дефолтный пользователь удален"}


@router.put("/default-users/reorder")
def reorder_default_users(
    data: DefaultUsersReorder,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Изменить порядок дефолтных пользователей"""
    for position, user_id in enumerate(data.user_ids):
        default_user = db.query(DefaultUser).filter(DefaultUser.user_id == user_id).first()
        if default_user:
            default_user.position = position
    
    db.commit()
    return {"message": "Порядок обновлен"}


# Поля сущностей
@router.get("/entity-types/{entity_type}/fields/{field_id}/values")
async def get_field_values(
    entity_type: str, 
    field_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить значения для поля (статусы, категории и т.д.)"""
    valid_types = ['deal', 'contact', 'company', 'lead']
    if entity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Недопустимый тип сущности. Допустимые: {', '.join(valid_types)}")
    
    try:
        bitrix_client = get_bitrix_client()
        
        # Получаем информацию о поле
        fields = await bitrix_client.get_entity_fields(entity_type)
        field_data = fields.get(field_id)
        
        if not field_data:
            raise HTTPException(status_code=404, detail=f"Поле {field_id} не найдено")
        
        field_type = field_data.get('type')
        status_type = field_data.get('statusType')
        
        values = []
        
        # Для полей типа crm_status получаем статусы
        if field_type == 'crm_status' and status_type:
            statuses = await bitrix_client.get_status_list(status_type)
            values = [
                {
                    'id': status.get('STATUS_ID') or status.get('ID'),
                    'name': status.get('NAME'),
                    'semantics': status.get('EXTRA', {}).get('SEMANTICS') if isinstance(status.get('EXTRA'), dict) else status.get('SEMANTICS')
                }
                for status in statuses
            ]
        
        # Для полей типа crm_category получаем категории
        elif field_type == 'crm_category':
            # Маппинг типов сущностей на entityTypeId
            entity_type_map = {
                'deal': 2,
                'contact': 3,
                'company': 4,
                'lead': 1
            }
            entity_type_id = entity_type_map.get(entity_type)
            if entity_type_id:
                categories = await bitrix_client.get_category_list(entity_type_id)
                values = [
                    {
                        'id': cat.get('id'),
                        'name': cat.get('name'),
                    }
                    for cat in categories
                ]
        
        return {
            "field_id": field_id,
            "field_type": field_type,
            "values": values
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения значений поля: {str(e)}")


@router.get("/entity-types/{entity_type}/fields")
async def get_entity_fields_by_type(
    entity_type: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить поля сущности из Bitrix24 по типу сущности"""
    valid_types = ['deal', 'contact', 'company', 'lead']
    if entity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Недопустимый тип сущности. Допустимые: {', '.join(valid_types)}")
    
    try:
        bitrix_client = get_bitrix_client()
        fields = await bitrix_client.get_entity_fields(entity_type)
        
        # Кэшируем поля в базу данных
        # Удаляем старые записи для этого типа сущности
        db.query(FieldMapping).filter(
            FieldMapping.entity_type == entity_type
        ).delete()
        
        # Добавляем новые записи
        for field_id, field_data in fields.items():
            field_mapping = FieldMapping(
                entity_type=entity_type,
                field_id=field_id,
                field_name=field_data.get('listLabel') or field_data.get('title') or field_id,
                field_type=field_data.get('type', 'string'),
                cached_at=datetime.now()
            )
            db.add(field_mapping)
        
        db.commit()
        
        return {
            "entity_type": entity_type,
            "fields": fields,
            "cached_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения полей: {str(e)}")


@router.get("/entity-types/{entity_type}/fields/{field_id}/category/{category_id}/stages")
async def get_category_stages(
    entity_type: str,
    field_id: str,
    category_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить стадии для конкретной категории (воронки)"""
    valid_types = ['deal', 'contact', 'company', 'lead']
    if entity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Недопустимый тип сущности. Допустимые: {', '.join(valid_types)}")
    
    try:
        bitrix_client = get_bitrix_client()
        # Маппинг типов сущностей на entityTypeId
        entity_type_map = {
            'deal': 2,
            'contact': 3,
            'company': 4,
            'lead': 1
        }
        entity_type_id = entity_type_map.get(entity_type)
        if not entity_type_id:
            raise HTTPException(status_code=400, detail="Недопустимый тип сущности")
        
        stages = await bitrix_client.get_category_stages(entity_type_id, category_id)
        
        values = []
        for stage in stages:
            # Стадии из crm.category.get имеют структуру с полями id, name, semantics
            # Стадии из crm.status.list имеют структуру с полями STATUS_ID, NAME, EXTRA
            stage_id = stage.get('id') or stage.get('STATUS_ID') or stage.get('ID')
            stage_name = stage.get('name') or stage.get('NAME')
            stage_semantics = stage.get('semantics') or (
                stage.get('EXTRA', {}).get('SEMANTICS') if isinstance(stage.get('EXTRA'), dict) else stage.get('SEMANTICS')
            )
            
            if stage_id and stage_name:
                values.append({
                    'id': str(stage_id),
                    'name': stage_name,
                    'semantics': stage_semantics
                })
        
        return {
            "field_id": field_id,
            "category_id": category_id,
            "values": values
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения стадий категории: {str(e)}")


@router.get("/rules/{rule_id}/fields")
async def get_entity_fields(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить поля сущности из Bitrix24 для правила"""
    rule = db.query(UpdateRule).filter(UpdateRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Правило не найдено")
    
    try:
        bitrix_client = get_bitrix_client()
        fields = await bitrix_client.get_entity_fields(rule.entity_type)
        
        # Кэшируем поля в базу данных
        # Удаляем старые записи для этого типа сущности
        db.query(FieldMapping).filter(
            FieldMapping.entity_type == rule.entity_type
        ).delete()
        
        # Добавляем новые записи
        for field_id, field_data in fields.items():
            field_mapping = FieldMapping(
                entity_type=rule.entity_type,
                field_id=field_id,
                field_name=field_data.get('listLabel') or field_data.get('title') or field_id,
                field_type=field_data.get('type', 'string'),
                cached_at=datetime.now()
            )
            db.add(field_mapping)
        
        db.commit()
        
        return {
            "entity_type": rule.entity_type,
            "fields": fields,
            "cached_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения полей: {str(e)}")


@router.get("/webhook")
def get_webhook_url(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Получить URL для настройки webhook в Bitrix24"""
    # Определяем базовый URL
    if settings.webhook_base_url:
        base_url = settings.webhook_base_url.rstrip('/')
    else:
        # Используем URL из запроса
        base_url = str(request.base_url).rstrip('/')
    
    webhook_url = f"{base_url}/api/webhook/bitrix"
    
    return {
        "webhook_url": webhook_url
    }
