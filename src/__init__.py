"""
🏠 Главный пакет Avito AI Responder

Автоматический респондер для Авито с ИИ-консультантом на базе Google Gemini.
Предназначен для автоматизации общения с покупателями и увеличения конверсии продаж.

Архитектура:
- core/         - Ядро системы (ИИ, обработка сообщений, генерация ответов)
- api/          - FastAPI веб-сервер и REST API
- integrations/ - Интеграции с внешними сервисами (Авито, Gemini)
- database/     - Работа с базой данных (модели, CRUD)
- services/     - Бизнес-сервисы (аналитика, уведомления, кеш)
- utils/        - Вспомогательные утилиты

Местоположение: src/__init__.py
"""

# Версия приложения
__version__ = "0.1.0-alpha"
__author__ = "Avito AI Responder Team"
__description__ = "Умный автоответчик для Авито с ИИ-консультантом"

# Основные компоненты (будут импортироваться по мере создания)
try:
    from .core import (
        CoreConfig,
        AIConsultant, 
        MessageHandler,
        ResponseGenerator,
        create_ai_consultant,
        create_message_handler,
        create_response_generator
    )
    CORE_AVAILABLE = True
except ImportError:
    CORE_AVAILABLE = False

# Информация о доступных модулях
AVAILABLE_MODULES = {
    "core": CORE_AVAILABLE,
    "api": False,           # Будет создан далее
    "integrations": False,  # Будет создан далее  
    "database": False,      # Будет создан далее
    "services": False,      # Будет создан далее
    "utils": False          # Будет создан далее
}

# Экспорт основных компонентов
__all__ = [
    "__version__",
    "__author__", 
    "__description__",
    "AVAILABLE_MODULES"
]

# Добавляем core компоненты если доступны
if CORE_AVAILABLE:
    __all__.extend([
        "CoreConfig",
        "AIConsultant",
        "MessageHandler", 
        "ResponseGenerator",
        "create_ai_consultant",
        "create_message_handler",
        "create_response_generator"
    ])


def get_version_info():
    """Получить детальную информацию о версии"""
    return {
        "version": __version__,
        "author": __author__,
        "description": __description__,
        "available_modules": AVAILABLE_MODULES
    }


def check_dependencies():
    """Проверить доступность основных зависимостей"""
    dependencies = {}
    
    # Проверяем основные библиотеки
    try:
        import google.generativeai
        dependencies["google-generativeai"] = True
    except ImportError:
        dependencies["google-generativeai"] = False
    
    try:
        import fastapi
        dependencies["fastapi"] = True
    except ImportError:
        dependencies["fastapi"] = False
    
    try:
        import sqlalchemy
        dependencies["sqlalchemy"] = True
    except ImportError:
        dependencies["sqlalchemy"] = False
    
    try:
        import redis
        dependencies["redis"] = True
    except ImportError:
        dependencies["redis"] = False
    
    return dependencies


def print_banner():
    """Вывести баннер приложения"""
    banner = f"""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                   🤖 AVITO AI RESPONDER                       ║
    ║                                                               ║
    ║  Умный автоответчик для Авито с ИИ-консультантом             ║
    ║  Версия: {__version__:<20} Автор: {__author__:<15} ║
    ║                                                               ║
    ║  📋 Доступные модули:                                         ║
    """
    
    for module, available in AVAILABLE_MODULES.items():
        status = "✅" if available else "❌"
        banner += f"    ║    {status} {module:<25}                              ║\n"
    
    banner += """    ║                                                               ║
    ║  🚀 Готов к автоматизации ваших продаж!                      ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    
    print(banner)