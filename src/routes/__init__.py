"""
API роуты для Авито ИИ-бота.

Этот модуль экспортирует все роутеры API для использования в основном приложении.
Каждый роутер отвечает за определенную область функциональности.
"""

from fastapi import APIRouter
from . import auth, users, messages, system

# Основной роутер для всех API эндпоинтов
api_router = APIRouter(prefix="/api/v1")

# Подключение всех роутеров с их префиксами и тегами
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"],
)

api_router.include_router(
    users.router,
    prefix="/users", 
    tags=["users"],
)

api_router.include_router(
    messages.router,
    prefix="/messages",
    tags=["messages"],
)

api_router.include_router(
    system.router,
    prefix="/system",
    tags=["system"],
)

__all__ = ["api_router"]