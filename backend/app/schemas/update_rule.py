from pydantic import BaseModel
from datetime import datetime, time
from typing import Dict, Any, Optional, List


class UserDistribution(BaseModel):
    """Процент распределения для пользователя"""
    user_id: int
    distribution_percentage: int = 100


class UpdateRuleBase(BaseModel):
    entity_type: str  # deal, contact, company, lead и т.д.
    entity_name: str  # Человекочитаемое название
    rule_type: str  # 'assigned_by_condition', 'field_condition', 'combined'
    condition_config: Dict[str, Any]  # JSON конфигурация условий
    priority: int = 0
    enabled: bool = True
    update_time: time  # Время обновления
    update_days: Optional[List[int]] = None  # JSON массив дней недели [1,2,3,4,5] или null для ежедневно
    user_distributions: List[UserDistribution] = []  # Список пользователей с процентами распределения
    # Обратная совместимость: user_ids для простоты использования
    user_ids: List[int] = []  # Список ID пользователей (используется для обратной совместимости)
    update_related_contacts_companies: bool = False  # Обновлять также связанные контакты и компании (только для deal)


class UpdateRuleCreate(UpdateRuleBase):
    pass


class UpdateRuleUpdate(BaseModel):
    entity_type: Optional[str] = None
    entity_name: Optional[str] = None
    rule_type: Optional[str] = None
    condition_config: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None
    update_time: Optional[time] = None
    update_days: Optional[List[int]] = None
    user_distributions: Optional[List[UserDistribution]] = None
    user_ids: Optional[List[int]] = None  # Для обратной совместимости
    update_related_contacts_companies: Optional[bool] = None


class UpdateRule(UpdateRuleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    # Обратная совместимость: distribution_percentage (устаревшее поле)
    distribution_percentage: Optional[int] = None
    # Переопределяем поле для обратной совместимости (может быть None в старых записях)
    update_related_contacts_companies: Optional[bool] = False
    
    class Config:
        from_attributes = True
    
    @classmethod
    def model_validate(cls, obj: Any, **kwargs):
        """Переопределяем валидацию для преобразования JSON строк в словари"""
        if hasattr(obj, 'condition_config_dict'):
            # Используем свойство для преобразования JSON строки в словарь
            obj_dict = {
                'id': obj.id,
                'entity_type': obj.entity_type,
                'entity_name': obj.entity_name,
                'rule_type': obj.rule_type,
                'condition_config': obj.condition_config_dict,
                'priority': obj.priority,
                'enabled': obj.enabled,
                'update_time': obj.update_time,
                'update_days': obj.update_days_list,
                'created_at': obj.created_at,
                'updated_at': obj.updated_at,
                'distribution_percentage': obj.distribution_percentage,
                'update_related_contacts_companies': bool(getattr(obj, 'update_related_contacts_companies', False) or False),
                'user_distributions': [],
                'user_ids': []
            }
            return cls(**obj_dict)
        return super().model_validate(obj, **kwargs)
