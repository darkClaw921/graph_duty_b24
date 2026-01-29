from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """Модель пользователя Bitrix24"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    default_user = relationship("DefaultUser", back_populates="user", uselist=False)
    duty_schedule_users = relationship("DutyScheduleUser", back_populates="user")
    update_rule_users = relationship("UpdateRuleUser", back_populates="user")
    update_rules = relationship("UpdateRule", secondary="update_rule_users", back_populates="users")
