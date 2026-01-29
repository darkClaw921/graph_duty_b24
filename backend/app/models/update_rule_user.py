from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class UpdateRuleUser(Base):
    """Промежуточная таблица для связи многие-ко-многим между правилами обновления и пользователями"""
    __tablename__ = "update_rule_users"
    
    id = Column(Integer, primary_key=True, index=True)
    update_rule_id = Column(Integer, ForeignKey("update_rules.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    distribution_percentage = Column(Integer, default=100)  # Процент распределения для конкретного пользователя
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    update_rule = relationship("UpdateRule", back_populates="rule_users")
    user = relationship("User", back_populates="update_rule_users")
    
    __table_args__ = (
        UniqueConstraint("update_rule_id", "user_id", name="uq_update_rule_user"),
    )
