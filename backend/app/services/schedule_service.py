from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date, datetime, timedelta
from typing import List, Optional
from app.models import DutySchedule, DutyScheduleUser, DefaultUser, User
from app.schemas.duty_schedule import DutyScheduleCreate, DutyScheduleUpdate
import logging

logger = logging.getLogger(__name__)


class ScheduleService:
    """Сервис для работы с графиком дежурств"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_schedule(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[DutySchedule]:
        """
        Получить график дежурств с фильтрацией по датам
        
        Args:
            start_date: Начальная дата (включительно)
            end_date: Конечная дата (включительно)
            
        Returns:
            Список записей графика дежурств
        """
        query = self.db.query(DutySchedule)
        
        if start_date:
            query = query.filter(DutySchedule.date >= start_date)
        if end_date:
            query = query.filter(DutySchedule.date <= end_date)
        
        return query.order_by(DutySchedule.date).all()
    
    def get_schedule_by_date(self, schedule_date: date) -> Optional[DutySchedule]:
        """Получить график на конкретную дату"""
        return self.db.query(DutySchedule).filter(
            DutySchedule.date == schedule_date
        ).first()
    
    def create_or_update_schedule(
        self,
        schedule_data: DutyScheduleCreate
    ) -> DutySchedule:
        """
        Создать или обновить запись в графике с несколькими пользователями
        
        Args:
            schedule_data: Данные для создания/обновления (с user_ids)
            
        Returns:
            Созданная или обновленная запись
        """
        existing = self.get_schedule_by_date(schedule_data.date)
        
        if existing:
            # Удаляем старые связи
            self.db.query(DutyScheduleUser).filter(
                DutyScheduleUser.duty_schedule_id == existing.id
            ).delete()
            
            # Создаем новые связи
            for user_id in schedule_data.user_ids:
                duty_user = DutyScheduleUser(
                    duty_schedule_id=existing.id,
                    user_id=user_id
                )
                self.db.add(duty_user)
            
            existing.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(existing)
            logger.info(f"Обновлен график на дату {schedule_data.date} с {len(schedule_data.user_ids)} пользователями")
            return existing
        else:
            schedule = DutySchedule(date=schedule_data.date)
            self.db.add(schedule)
            self.db.flush()  # Получаем ID для schedule
            
            # Создаем связи с пользователями
            for user_id in schedule_data.user_ids:
                duty_user = DutyScheduleUser(
                    duty_schedule_id=schedule.id,
                    user_id=user_id
                )
                self.db.add(duty_user)
            
            self.db.commit()
            self.db.refresh(schedule)
            logger.info(f"Создан график на дату {schedule_data.date} с {len(schedule_data.user_ids)} пользователями")
            return schedule
    
    def delete_schedule(self, schedule_id: int) -> bool:
        """Удалить запись из графика"""
        schedule = self.db.query(DutySchedule).filter(
            DutySchedule.id == schedule_id
        ).first()
        
        if schedule:
            self.db.delete(schedule)
            self.db.commit()
            logger.info(f"Удален график с ID {schedule_id}")
            return True
        return False
    
    def generate_schedule_for_month(
        self,
        year: int,
        month: int
    ) -> List[DutySchedule]:
        """
        Сгенерировать график на месяц из дефолтных пользователей
        
        Пользователи распределяются циклически по дням месяца
        
        Args:
            year: Год
            month: Месяц (1-12)
            
        Returns:
            Список созданных записей графика
        """
        # Получаем дефолтных пользователей, отсортированных по position
        default_users = self.db.query(DefaultUser).join(User).filter(
            User.active == True
        ).order_by(DefaultUser.position).all()
        
        if not default_users:
            raise ValueError("Нет дефолтных пользователей для генерации графика")
        
        # Определяем диапазон дат месяца
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # Удаляем существующие записи за этот месяц
        self.db.query(DutySchedule).filter(
            and_(
                DutySchedule.date >= start_date,
                DutySchedule.date <= end_date
            )
        ).delete()
        
        # Генерируем график
        created_schedules = []
        current_date = start_date
        user_index = 0
        
        while current_date <= end_date:
            default_user = default_users[user_index % len(default_users)]
            
            schedule = DutySchedule(date=current_date)
            self.db.add(schedule)
            self.db.flush()  # Получаем ID для schedule
            
            # Создаем связь с пользователем
            duty_user = DutyScheduleUser(
                duty_schedule_id=schedule.id,
                user_id=default_user.user_id
            )
            self.db.add(duty_user)
            created_schedules.append(schedule)
            
            current_date += timedelta(days=1)
            user_index += 1
        
        self.db.commit()
        
        # Обновляем created_at для всех созданных записей
        for schedule in created_schedules:
            self.db.refresh(schedule)
        
        logger.info(f"Сгенерирован график на {month}/{year} для {len(created_schedules)} дней")
        return created_schedules
    
    def get_duty_users_for_date(self, schedule_date: date) -> List[User]:
        """
        Получить список пользователей на дежурстве на конкретную дату
        
        Args:
            schedule_date: Дата дежурства
            
        Returns:
            Список пользователей на дежурстве
        """
        schedule = self.get_schedule_by_date(schedule_date)
        if schedule:
            duty_users = self.db.query(DutyScheduleUser).filter(
                DutyScheduleUser.duty_schedule_id == schedule.id
            ).all()
            
            user_ids = [du.user_id for du in duty_users]
            if user_ids:
                return self.db.query(User).filter(User.id.in_(user_ids)).all()
        return []
