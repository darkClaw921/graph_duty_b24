from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import json
from typing import Dict, Any, List, Optional


class UpdateRule(Base):
    """Правила обновления сущностей"""
    __tablename__ = "update_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False, index=True)  # deal, contact, company, lead и т.д.
    entity_name = Column(String, nullable=False)  # Человекочитаемое название
    rule_type = Column(String, nullable=False)  # 'assigned_by_condition', 'field_condition', 'combined'
    condition_config = Column(Text, nullable=False)  # JSON конфигурация условий
    priority = Column(Integer, nullable=False, default=0)  # Приоритет правила (меньше = выше приоритет)
    enabled = Column(Boolean, default=True)
    update_time = Column(Time, nullable=False)  # Время обновления (например, 09:00)
    update_days = Column(Text, nullable=True)  # JSON массив дней недели [1,2,3,4,5] или null для ежедневно
    distribution_percentage = Column(Integer, default=100)  # Процент распределения сущностей между пользователями (100 = равномерно)
    update_related_contacts_companies = Column(Boolean, default=False)  # Обновлять также связанные контакты и компании (только для deal)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    rule_users = relationship("UpdateRuleUser", back_populates="update_rule", cascade="all, delete-orphan")
    users = relationship("User", secondary="update_rule_users", back_populates="update_rules")
    
    @property
    def condition_config_dict(self) -> Dict[str, Any]:
        """Преобразует condition_config из JSON строки в словарь"""
        if isinstance(self.condition_config, str):
            try:
                return json.loads(self.condition_config)
            except (json.JSONDecodeError, TypeError):
                return {}
        return self.condition_config if isinstance(self.condition_config, dict) else {}
    
    @property
    def update_days_list(self) -> Optional[List[int]]:
        """Преобразует update_days из JSON строки в список"""
        if not self.update_days:
            return None
        if isinstance(self.update_days, str):
            try:
                return json.loads(self.update_days)
            except (json.JSONDecodeError, TypeError):
                return None
        return self.update_days if isinstance(self.update_days, list) else None
