from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class UpdateSource(str, enum.Enum):
    """Источник обновления"""
    WEBHOOK = "webhook"
    SCHEDULED = "scheduled"
    MANUAL = "manual"


class UpdateHistory(Base):
    """Модель истории изменений ответственных в сущностях Bitrix24"""
    __tablename__ = "update_history"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False, index=True)  # deal, contact, company, lead
    entity_id = Column(Integer, nullable=False, index=True)
    old_assigned_by_id = Column(Integer, nullable=True)  # От кого изменено
    new_assigned_by_id = Column(Integer, nullable=False)  # На кого изменено
    update_source = Column(SQLEnum(UpdateSource), nullable=False, default=UpdateSource.MANUAL)
    rule_id = Column(Integer, ForeignKey("update_rules.id"), nullable=True)
    related_entity_type = Column(String, nullable=True)  # Тип связанной сущности (если обновление зависимой)
    related_entity_id = Column(Integer, nullable=True)  # ID связанной сущности
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    rule = relationship("UpdateRule", backref="update_histories")
