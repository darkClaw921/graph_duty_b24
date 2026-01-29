from sqlalchemy import Column, Integer, Date, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class DutySchedule(Base):
    """График дежурств"""
    __tablename__ = "duty_schedule"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    duty_users = relationship("DutyScheduleUser", back_populates="duty_schedule", cascade="all, delete-orphan")
    
    __table_args__ = (UniqueConstraint("date", name="uq_duty_schedule_date"),)
