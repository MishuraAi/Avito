"""
Минимальная версия роутеров - только auth для Avito callback
ВРЕМЕННО отключаем сложные роуты до исправления зависимостей
"""

from fastapi import APIRouter

# Создаем главный роутер
main_router = APIRouter()

# Импортируем только auth роутер (исправленный)
try:
    from . import auth
    main_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
    print("✅ Auth router загружен успешно")
except Exception as e:
    print(f"❌ Ошибка загрузки auth router: {e}")

# ВРЕМЕННО отключаем проблемные роуты
# from . import users, messages, system

__all__ = ["main_router"]