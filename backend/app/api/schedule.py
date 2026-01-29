from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.database import get_db
from app.models import DutySchedule, DutyScheduleUser, User
from app.schemas.duty_schedule import (
    DutySchedule as DutyScheduleSchema,
    DutyScheduleCreate,
    DutyScheduleUpdate,
    DutyScheduleWithUsers,
    DutyScheduleUserInfo
)
from app.services.schedule_service import ScheduleService
from app.auth.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


@router.get("", response_model=List[DutyScheduleWithUsers])
def get_schedule(
    start_date: Optional[date] = Query(None, description="Начальная дата (включительно)"),
    end_date: Optional[date] = Query(None, description="Конечная дата (включительно)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить график дежурств с фильтрацией по датам"""
    service = ScheduleService(db)
    schedules = service.get_schedule(start_date, end_date)
    
    # Добавляем информацию о пользователях
    result = []
    for schedule in schedules:
        duty_users = db.query(DutyScheduleUser).filter(
            DutyScheduleUser.duty_schedule_id == schedule.id
        ).all()
        
        users_info = []
        for duty_user in duty_users:
            user = db.query(User).filter(User.id == duty_user.user_id).first()
            if user:
                users_info.append(DutyScheduleUserInfo(
                    user_id=user.id,
                    user_name=f"{user.name or ''} {user.last_name or ''}".strip() or None,
                    user_email=user.email
                ))
        
        result.append(DutyScheduleWithUsers(
            id=schedule.id,
            date=schedule.date,
            users=users_info,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at
        ))
    
    return result


@router.get("/{schedule_date}", response_model=DutyScheduleWithUsers)
def get_schedule_by_date(
    schedule_date: date,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить график на конкретную дату"""
    service = ScheduleService(db)
    schedule = service.get_schedule_by_date(schedule_date)
    
    if not schedule:
        raise HTTPException(status_code=404, detail="График на эту дату не найден")
    
    duty_users = db.query(DutyScheduleUser).filter(
        DutyScheduleUser.duty_schedule_id == schedule.id
    ).all()
    
    users_info = []
    for duty_user in duty_users:
        user = db.query(User).filter(User.id == duty_user.user_id).first()
        if user:
            users_info.append(DutyScheduleUserInfo(
                user_id=user.id,
                user_name=f"{user.name or ''} {user.last_name or ''}".strip() or None,
                user_email=user.email
            ))
    
    return DutyScheduleWithUsers(
        id=schedule.id,
        date=schedule.date,
        users=users_info,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at
    )


@router.post("", response_model=DutyScheduleWithUsers)
def create_schedule(
    schedule_data: DutyScheduleCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Создать или обновить запись в графике"""
    try:
        if not schedule_data.user_ids:
            raise HTTPException(status_code=400, detail="Необходимо указать хотя бы одного пользователя")
        
        service = ScheduleService(db)
        schedule = service.create_or_update_schedule(schedule_data)
        
        # Получаем информацию о пользователях
        duty_users = db.query(DutyScheduleUser).filter(
            DutyScheduleUser.duty_schedule_id == schedule.id
        ).all()
        
        users_info = []
        for duty_user in duty_users:
            user = db.query(User).filter(User.id == duty_user.user_id).first()
            if user:
                users_info.append(DutyScheduleUserInfo(
                    user_id=user.id,
                    user_name=f"{user.name or ''} {user.last_name or ''}".strip() or None,
                    user_email=user.email
                ))
        
        return DutyScheduleWithUsers(
            id=schedule.id,
            date=schedule.date,
            users=users_info,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Ошибка при создании графика: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания графика: {str(e)}")


@router.put("/{schedule_id}", response_model=DutyScheduleWithUsers)
def update_schedule(
    schedule_id: int,
    schedule_data: DutyScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Обновить запись в графике"""
    schedule = db.query(DutySchedule).filter(DutySchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Запись графика не найдена")
    
    if schedule_data.user_ids is not None:
        # Удаляем старые связи
        db.query(DutyScheduleUser).filter(
            DutyScheduleUser.duty_schedule_id == schedule_id
        ).delete()
        
        # Создаем новые связи
        for user_id in schedule_data.user_ids:
            duty_user = DutyScheduleUser(
                duty_schedule_id=schedule_id,
                user_id=user_id
            )
            db.add(duty_user)
    
    db.commit()
    db.refresh(schedule)
    
    # Получаем информацию о пользователях
    duty_users = db.query(DutyScheduleUser).filter(
        DutyScheduleUser.duty_schedule_id == schedule_id
    ).all()
    
    users_info = []
    for duty_user in duty_users:
        user = db.query(User).filter(User.id == duty_user.user_id).first()
        if user:
            users_info.append(DutyScheduleUserInfo(
                user_id=user.id,
                user_name=f"{user.name or ''} {user.last_name or ''}".strip() or None,
                user_email=user.email
            ))
    
    return DutyScheduleWithUsers(
        id=schedule.id,
        date=schedule.date,
        users=users_info,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at
    )


@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Удалить запись из графика"""
    service = ScheduleService(db)
    if service.delete_schedule(schedule_id):
        return {"message": "Запись удалена"}
    raise HTTPException(status_code=404, detail="Запись графика не найдена")


@router.post("/generate")
def generate_schedule(
    year: int = Query(..., description="Год"),
    month: int = Query(..., description="Месяц (1-12)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Сгенерировать график на месяц из дефолтных пользователей"""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="Месяц должен быть от 1 до 12")
    
    try:
        service = ScheduleService(db)
        schedules = service.generate_schedule_for_month(year, month)
        return {
            "message": f"График сгенерирован на {month}/{year}",
            "count": len(schedules)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации графика: {str(e)}")
