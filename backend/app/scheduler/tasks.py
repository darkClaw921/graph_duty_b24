from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, date, time
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import UpdateRule
from app.services.update_service import UpdateService
from app.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def daily_update_task():
    """Задача ежедневного обновления ответственных"""
    db = SessionLocal()
    try:
        logger.info("Запуск ежедневного обновления ответственных")
        update_service = UpdateService(db)
        today = date.today()
        now = datetime.now()
        
        # Получаем все включенные правила
        rules = db.query(UpdateRule).filter(
            UpdateRule.enabled == True
        ).all()
        
        async def run_updates():
            updated_count = 0
            skipped_count = 0
            
            for rule in rules:
                # Проверяем, нужно ли обновлять для этого правила
                if update_service.should_update_rule(rule, now):
                    try:
                        result = await update_service.update_entities_for_date(today)
                        updated_count += result.get('updated_entities', 0)
                        logger.info(
                            f"Обновлено сущностей для правила {rule.id} ({rule.entity_name}): "
                            f"{result.get('updated_entities', 0)}"
                        )
                    except Exception as e:
                        logger.error(f"Ошибка при обновлении правила {rule.id} ({rule.entity_name}): {e}")
                else:
                    skipped_count += 1
                    logger.debug(f"Пропущено обновление для правила {rule.id} ({rule.entity_name})")
            
            logger.info(
                f"Ежедневное обновление завершено. Обновлено сущностей: {updated_count}, "
                f"пропущено правил: {skipped_count}"
            )
        
        # Запускаем async функцию
        asyncio.run(run_updates())
    except Exception as e:
        logger.error(f"Критическая ошибка при ежедневном обновлении: {e}")
    finally:
        db.close()


def start_scheduler():
    """Запустить планировщик задач"""
    if not settings.scheduler_enabled:
        logger.info("Планировщик отключен в настройках")
        return
    
    # Парсим время обновления по умолчанию
    default_time = settings.default_update_time.split(':')
    hour = int(default_time[0])
    minute = int(default_time[1]) if len(default_time) > 1 else 0
    
    # Добавляем задачу на ежедневное выполнение
    scheduler.add_job(
        daily_update_task,
        trigger=CronTrigger(hour=hour, minute=minute),
        id='daily_update',
        name='Ежедневное обновление ответственных',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"Планировщик запущен. Ежедневное обновление в {settings.default_update_time}")


def stop_scheduler():
    """Остановить планировщик задач"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Планировщик остановлен")
