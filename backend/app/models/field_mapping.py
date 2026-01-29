from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base


class FieldMapping(Base):
    """Маппинг полей Bitrix24"""
    __tablename__ = "field_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False, index=True)  # Тип сущности
    field_id = Column(String, nullable=False)  # ID поля в Bitrix24 (например, ASSIGNED_BY_ID, UF_CRM_123)
    field_name = Column(String, nullable=False)  # Человекочитаемое название поля
    field_type = Column(String, nullable=False)  # Тип поля (user, string, integer, date, etc.)
    cached_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
