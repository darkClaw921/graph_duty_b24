from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import UpdateRule, UpdateRuleUser, User
from app.schemas.update_rule import (
    UpdateRule as UpdateRuleSchema,
    UpdateRuleCreate,
    UpdateRuleUpdate
)
from app.auth.dependencies import get_current_user
import json

router = APIRouter(prefix="/api/settings", tags=["rules"])


@router.get("/rules", response_model=List[UpdateRuleSchema])
def get_rules(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить все правила обновления"""
    rules = db.query(UpdateRule).order_by(UpdateRule.priority, UpdateRule.id).all()
    
    # Добавляем user_distributions и user_ids к каждому правилу
    result = []
    for rule in rules:
        # Преобразуем condition_config и update_days из JSON строк в словари/списки
        condition_config_dict = json.loads(rule.condition_config) if isinstance(rule.condition_config, str) else rule.condition_config
        update_days_list = json.loads(rule.update_days) if rule.update_days and isinstance(rule.update_days, str) else rule.update_days
        
        rule_dict = UpdateRuleSchema(
            id=rule.id,
            entity_type=rule.entity_type,
            entity_name=rule.entity_name,
            rule_type=rule.rule_type,
            condition_config=condition_config_dict,
            priority=rule.priority,
            enabled=rule.enabled,
            update_time=rule.update_time,
            update_days=update_days_list,
            created_at=rule.created_at,
            updated_at=rule.updated_at,
            distribution_percentage=rule.distribution_percentage,
            update_related_contacts_companies=bool(getattr(rule, 'update_related_contacts_companies', False) or False),
            user_distributions=[],
            user_ids=[]
        )
        # Формируем список распределений пользователей
        user_distributions = [
            {"user_id": ru.user_id, "distribution_percentage": ru.distribution_percentage or 100}
            for ru in rule.rule_users
        ]
        rule_dict.user_distributions = user_distributions
        # Для обратной совместимости также добавляем user_ids
        rule_dict.user_ids = [ru.user_id for ru in rule.rule_users]
        result.append(rule_dict)
    
    return result


@router.post("/rules", response_model=UpdateRuleSchema)
def create_rule(
    data: UpdateRuleCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Создать правило обновления"""
    # Преобразуем condition_config и update_days в JSON строки
    condition_config_json = json.dumps(data.condition_config)
    update_days_json = None
    if data.update_days:
        update_days_json = json.dumps(data.update_days)
    
    # Создаем правило
    rule = UpdateRule(
        entity_type=data.entity_type,
        entity_name=data.entity_name,
        rule_type=data.rule_type,
        condition_config=condition_config_json,
        priority=data.priority,
        enabled=data.enabled,
        update_time=data.update_time,
        update_days=update_days_json,
        distribution_percentage=100,  # Устаревшее поле, оставляем для обратной совместимости
        update_related_contacts_companies=bool(getattr(data, 'update_related_contacts_companies', False) or False)
    )
    db.add(rule)
    db.flush()  # Получаем ID правила
    
    # Добавляем пользователей с процентами распределения
    # Используем user_distributions если указано, иначе user_ids (для обратной совместимости)
    users_to_add = []
    if data.user_distributions:
        users_to_add = data.user_distributions
    elif data.user_ids:
        # Если указаны только user_ids, используем равномерное распределение
        users_to_add = [{"user_id": uid, "distribution_percentage": 100} for uid in data.user_ids]
    
    for user_dist in users_to_add:
        # Обрабатываем как Pydantic модель или словарь
        if hasattr(user_dist, 'user_id'):
            user_id = user_dist.user_id
            percentage = getattr(user_dist, 'distribution_percentage', 100)
        else:
            user_id = user_dist.get("user_id") if isinstance(user_dist, dict) else user_dist
            percentage = user_dist.get("distribution_percentage", 100) if isinstance(user_dist, dict) else 100
        
        # Проверяем существование пользователя
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Пользователь с ID {user_id} не найден")
        
        rule_user = UpdateRuleUser(
            update_rule_id=rule.id,
            user_id=user_id,
            distribution_percentage=percentage
        )
        db.add(rule_user)
    
    db.commit()
    db.refresh(rule)
    
    # Возвращаем правило с user_distributions и user_ids
    # Преобразуем condition_config и update_days из JSON строк в словари/списки
    condition_config_dict = json.loads(rule.condition_config) if isinstance(rule.condition_config, str) else rule.condition_config
    update_days_list = json.loads(rule.update_days) if rule.update_days and isinstance(rule.update_days, str) else rule.update_days
    
    result = UpdateRuleSchema(
        id=rule.id,
        entity_type=rule.entity_type,
        entity_name=rule.entity_name,
        rule_type=rule.rule_type,
        condition_config=condition_config_dict,
        priority=rule.priority,
        enabled=rule.enabled,
        update_time=rule.update_time,
        update_days=update_days_list,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
        distribution_percentage=rule.distribution_percentage,
        update_related_contacts_companies=getattr(rule, 'update_related_contacts_companies', False),
        user_distributions=[],
        user_ids=[]
    )
    user_distributions = [
        {"user_id": ru.user_id, "distribution_percentage": ru.distribution_percentage or 100}
        for ru in rule.rule_users
    ]
    result.user_distributions = user_distributions
    result.user_ids = [ru.user_id for ru in rule.rule_users]
    return result


@router.get("/rules/{rule_id}", response_model=UpdateRuleSchema)
def get_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить правило по ID"""
    rule = db.query(UpdateRule).filter(UpdateRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Правило не найдено")
    
    # Преобразуем condition_config и update_days из JSON строк в словари/списки
    condition_config_dict = json.loads(rule.condition_config) if isinstance(rule.condition_config, str) else rule.condition_config
    update_days_list = json.loads(rule.update_days) if rule.update_days and isinstance(rule.update_days, str) else rule.update_days
    
    result = UpdateRuleSchema(
        id=rule.id,
        entity_type=rule.entity_type,
        entity_name=rule.entity_name,
        rule_type=rule.rule_type,
        condition_config=condition_config_dict,
        priority=rule.priority,
        enabled=rule.enabled,
        update_time=rule.update_time,
        update_days=update_days_list,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
        distribution_percentage=rule.distribution_percentage,
        update_related_contacts_companies=getattr(rule, 'update_related_contacts_companies', False),
        user_distributions=[],
        user_ids=[]
    )
    user_distributions = [
        {"user_id": ru.user_id, "distribution_percentage": ru.distribution_percentage or 100}
        for ru in rule.rule_users
    ]
    result.user_distributions = user_distributions
    result.user_ids = [ru.user_id for ru in rule.rule_users]
    return result


@router.put("/rules/{rule_id}", response_model=UpdateRuleSchema)
def update_rule(
    rule_id: int,
    data: UpdateRuleUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Обновить правило обновления"""
    rule = db.query(UpdateRule).filter(UpdateRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Правило не найдено")
    
    if data.entity_type is not None:
        rule.entity_type = data.entity_type
    if data.entity_name is not None:
        rule.entity_name = data.entity_name
    if data.rule_type is not None:
        rule.rule_type = data.rule_type
    if data.condition_config is not None:
        rule.condition_config = json.dumps(data.condition_config)
    if data.priority is not None:
        rule.priority = data.priority
    if data.enabled is not None:
        rule.enabled = data.enabled
    if data.update_time is not None:
        rule.update_time = data.update_time
    if data.update_days is not None:
        rule.update_days = json.dumps(data.update_days) if data.update_days else None
    if data.update_related_contacts_companies is not None:
        rule.update_related_contacts_companies = data.update_related_contacts_companies
    # Обновляем пользователей если указаны
    if data.user_distributions is not None or data.user_ids is not None:
        # Удаляем старые связи
        db.query(UpdateRuleUser).filter(UpdateRuleUser.update_rule_id == rule_id).delete()
        
        # Определяем список пользователей для добавления
        users_to_add = []
        if data.user_distributions:
            users_to_add = data.user_distributions
        elif data.user_ids:
            # Если указаны только user_ids, используем равномерное распределение
            users_to_add = [{"user_id": uid, "distribution_percentage": 100} for uid in data.user_ids]
        
        # Добавляем новых пользователей с процентами
        for user_dist in users_to_add:
            # Обрабатываем как Pydantic модель или словарь
            if hasattr(user_dist, 'user_id'):
                user_id = user_dist.user_id
                percentage = getattr(user_dist, 'distribution_percentage', 100)
            else:
                user_id = user_dist.get("user_id") if isinstance(user_dist, dict) else user_dist
                percentage = user_dist.get("distribution_percentage", 100) if isinstance(user_dist, dict) else 100
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                db.rollback()
                raise HTTPException(status_code=404, detail=f"Пользователь с ID {user_id} не найден")
            
            rule_user = UpdateRuleUser(
                update_rule_id=rule_id,
                user_id=user_id,
                distribution_percentage=percentage
            )
            db.add(rule_user)
    
    db.commit()
    db.refresh(rule)
    
    # Преобразуем condition_config и update_days из JSON строк в словари/списки
    condition_config_dict = json.loads(rule.condition_config) if isinstance(rule.condition_config, str) else rule.condition_config
    update_days_list = json.loads(rule.update_days) if rule.update_days and isinstance(rule.update_days, str) else rule.update_days
    
    result = UpdateRuleSchema(
        id=rule.id,
        entity_type=rule.entity_type,
        entity_name=rule.entity_name,
        rule_type=rule.rule_type,
        condition_config=condition_config_dict,
        priority=rule.priority,
        enabled=rule.enabled,
        update_time=rule.update_time,
        update_days=update_days_list,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
        distribution_percentage=rule.distribution_percentage,
        update_related_contacts_companies=getattr(rule, 'update_related_contacts_companies', False),
        user_distributions=[],
        user_ids=[]
    )
    user_distributions = [
        {"user_id": ru.user_id, "distribution_percentage": ru.distribution_percentage or 100}
        for ru in rule.rule_users
    ]
    result.user_distributions = user_distributions
    result.user_ids = [ru.user_id for ru in rule.rule_users]
    return result


@router.delete("/rules/{rule_id}")
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Удалить правило обновления"""
    rule = db.query(UpdateRule).filter(UpdateRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Правило не найдено")
    
    db.delete(rule)
    db.commit()
    return {"message": "Правило удалено"}


@router.get("/rules/{rule_id}/users", response_model=List[int])
def get_rule_users(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить список пользователей правила"""
    rule = db.query(UpdateRule).filter(UpdateRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Правило не найдено")
    
    user_ids = [ru.user_id for ru in rule.rule_users]
    return user_ids


@router.post("/rules/{rule_id}/users/{user_id}")
def add_user_to_rule(
    rule_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Добавить пользователя в правило"""
    rule = db.query(UpdateRule).filter(UpdateRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Правило не найдено")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Проверяем, не добавлен ли уже
    existing = db.query(UpdateRuleUser).filter(
        UpdateRuleUser.update_rule_id == rule_id,
        UpdateRuleUser.user_id == user_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Пользователь уже добавлен в правило")
    
    rule_user = UpdateRuleUser(
        update_rule_id=rule_id,
        user_id=user_id
    )
    db.add(rule_user)
    db.commit()
    return {"message": "Пользователь добавлен в правило"}


@router.delete("/rules/{rule_id}/users/{user_id}")
def remove_user_from_rule(
    rule_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Удалить пользователя из правила"""
    rule_user = db.query(UpdateRuleUser).filter(
        UpdateRuleUser.update_rule_id == rule_id,
        UpdateRuleUser.user_id == user_id
    ).first()
    
    if not rule_user:
        raise HTTPException(status_code=404, detail="Связь пользователя с правилом не найдена")
    
    db.delete(rule_user)
    db.commit()
    return {"message": "Пользователь удален из правила"}
