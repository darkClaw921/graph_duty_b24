from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List


class DutyScheduleBase(BaseModel):
    date: date
    user_ids: List[int]  # Список ID пользователей


class DutyScheduleCreate(DutyScheduleBase):
    pass


class DutyScheduleUpdate(BaseModel):
    user_ids: Optional[List[int]] = None


class DutySchedule(DutyScheduleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DutyScheduleUserInfo(BaseModel):
    user_id: int
    user_name: Optional[str] = None
    user_email: Optional[str] = None


class DutyScheduleWithUsers(BaseModel):
    id: int
    date: date
    users: List[DutyScheduleUserInfo]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
