from fastapi import APIRouter
from app.api import users, schedule, settings, rules, utils, webhook, history, auth

api_router = APIRouter()

# Роутер авторизации (без защиты)
api_router.include_router(auth.router)

# Роутер webhook (без защиты, так как вызывается извне)
api_router.include_router(webhook.router)

# Защищенные роутеры
api_router.include_router(users.router)
api_router.include_router(schedule.router)
api_router.include_router(settings.router)
api_router.include_router(rules.router)
api_router.include_router(utils.router)
api_router.include_router(history.router)
