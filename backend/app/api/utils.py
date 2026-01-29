from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional
from app.database import get_db
from app.services.update_service import UpdateService
from app.auth.dependencies import get_current_user
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/utils", tags=["utils"])


@router.post("/update-now")
async def update_entities_now(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Принудительное обновление ответственных сейчас"""
    try:
        service = UpdateService(db)
        result = await service.update_entities_now()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обновления: {str(e)}")


@router.get("/update-count")
async def get_update_count(
    update_date: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить количество сущностей, которые будут обновлены"""
    try:
        service = UpdateService(db)
        if update_date:
            target_date = date.fromisoformat(update_date)
        else:
            target_date = date.today()
        
        result = await service.get_entities_count_for_date(target_date)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения количества: {str(e)}")


@router.post("/update-now-stream")
async def update_entities_now_stream(
    update_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Принудительное обновление ответственных с прогрессом через streaming"""
    try:
        logger.info(f"Запрос на streaming обновление для даты: {update_date}")
        service = UpdateService(db)
        if update_date:
            target_date = date.fromisoformat(update_date)
        else:
            target_date = date.today()
        
        logger.info(f"Целевая дата: {target_date}")
        
        async def generate():
            try:
                logger.info("Начало генерации прогресса")
                async for progress in service.update_entities_for_date_with_progress(target_date):
                    logger.info(f"Отправка прогресса: {progress.get('type', 'unknown')}")
                    data = f"data: {json.dumps(progress, ensure_ascii=False)}\n\n"
                    yield data
                logger.info("Генерация прогресса завершена")
            except Exception as e:
                logger.error(f"Ошибка в генераторе: {e}", exc_info=True)
                # Отправляем ошибку через stream
                error_progress = {
                    "type": "error",
                    "error": str(e),
                    "date": str(target_date)
                }
                yield f"data: {json.dumps(error_progress, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )
    except Exception as e:
        logger.error(f"Ошибка при создании streaming response: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка обновления: {str(e)}")


@router.get("/preview-updates")
async def get_preview_updates(
    update_date: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить предпросмотр сущностей, которые будут обновлены (без реального обновления)"""
    try:
        service = UpdateService(db)
        if update_date:
            target_date = date.fromisoformat(update_date)
        else:
            target_date = date.today()
        
        result = await service.get_preview_updates(target_date)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения предпросмотра: {str(e)}")


@router.get("/health")
def health_check():
    """Проверка здоровья сервиса (публичный endpoint для healthcheck)"""
    return {"status": "ok", "service": "Graph Duty B24"}
