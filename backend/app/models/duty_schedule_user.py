from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class DutyScheduleUser(Base):
    """Промежуточная таблица для связи многие-ко-многим между графиком дежурств и пользователями"""
    __tablename__ = "duty_schedule_users"
    
    id = Column(Integer, primary_key=True, index=True)
    duty_schedule_id = Column(Integer, ForeignKey("duty_schedule.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    duty_schedule = relationship("DutySchedule", back_populates="duty_users")
    user = relationship("User", back_populates="duty_schedule_users")
    
    __table_args__ = (
        UniqueConstraint("duty_schedule_id", "user_id", name="uq_duty_schedule_user"),
    )
