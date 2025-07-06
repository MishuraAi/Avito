"""
🌐 FastAPI приложение для Avito AI Responder

Этот пакет содержит все компоненты REST API:
- main.py        - Главное FastAPI приложение
- routes/        - Роуты API (endpoints)
- middleware/    - Middleware компоненты
- dependencies/  - Dependency injection
- schemas/       - Pydantic схемы для API

Местоположение: src/api/__init__.py
"""

from typing import Dict, Any, List
import logging

# Настройка логгера
logger = logging.getLogger(__name__)

# Будут импортироваться по мере создания
try:
    from .main import app, create_app
    MAIN_APP_AVAILABLE = True
except ImportError:
    MAIN_APP_AVAILABLE = False

try:
    from .routes import *
    ROUTES_AVAILABLE = True
except ImportError:
    ROUTES_AVAILABLE = False

try:
    from .middleware import *
    MIDDLEWARE_AVAILABLE = True
except ImportError:
    MIDDLEWARE_AVAILABLE = False

try:
    from .dependencies import *
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False

try:
    from .schemas import *
    SCHEMAS_AVAILABLE = True
except ImportError:
    SCHEMAS_AVAILABLE = False


# Информация о доступности API компонентов
AVAILABLE_API_COMPONENTS = {
    "main_app": MAIN_APP_AVAILABLE,
    "routes": ROUTES_AVAILABLE,
    "middleware": MIDDLEWARE_AVAILABLE,
    "dependencies": DEPENDENCIES_AVAILABLE,
    "schemas": SCHEMAS_AVAILABLE
}

# Версия API
__version__ = "1.0.0"
API_VERSION = "v1"

# Метаданные API
API_METADATA = {
    "title": "Avito AI Responder API",
    "description": """
    🤖 **Умный автоответчик для Авито**
    
    Этот API предоставляет все возможности для автоматизации общения на Авито:
    
    ## 🎯 Основные возможности
    
    * **👥 Управление пользователями** - регистрация, профили, настройки
    * **💬 Обработка сообщений** - получение, анализ, автоответы
    * **🤖 ИИ-консультант** - генерация умных ответов на базе Gemini
    * **📊 Аналитика** - статистика диалогов, конверсия, метрики
    * **⚙️ Настройки** - персонализация поведения бота
    * **🔗 Интеграции** - подключение к Авито API
    
    ## 🔐 Аутентификация
    
    API использует JWT токены для аутентификации продавцов.
    
    ## 📈 Rate Limiting
    
    Применяются лимиты запросов в зависимости от тарифного плана.
    """,
    "version": __version__,
    "contact": {
        "name": "Avito AI Responder Support",
        "email": "support@avito-ai-responder.com"
    },
    "license": {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
}

# Теги для группировки endpoints
API_TAGS = [
    {
        "name": "auth",
        "description": "🔐 Аутентификация и авторизация"
    },
    {
        "name": "users", 
        "description": "👥 Управление пользователями и покупателями"
    },
    {
        "name": "sellers",
        "description": "🏪 Управление продавцами и их настройками"
    },
    {
        "name": "messages",
        "description": "💬 Сообщения и диалоги"
    },
    {
        "name": "conversations",
        "description": "🗨️ Управление диалогами"
    },
    {
        "name": "templates", 
        "description": "📝 Шаблоны сообщений"
    },
    {
        "name": "ai",
        "description": "🤖 ИИ-анализ и генерация ответов"
    },
    {
        "name": "analytics",
        "description": "📊 Аналитика и статистика"
    },
    {
        "name": "integrations",
        "description": "🔗 Интеграции с внешними сервисами"
    },
    {
        "name": "system",
        "description": "⚙️ Системная информация и health checks"
    }
]

# Экспортируемые компоненты
__all__ = [
    # Метаданные
    "__version__",
    "API_VERSION", 
    "API_METADATA",
    "API_TAGS",
    "AVAILABLE_API_COMPONENTS"
]

# Добавляем доступные компоненты в экспорт
if MAIN_APP_AVAILABLE:
    __all__.extend([
        "app",
        "create_app"
    ])


def get_api_info() -> Dict[str, Any]:
    """Получение информации об API"""
    
    return {
        "version": __version__,
        "api_version": API_VERSION,
        "available_components": AVAILABLE_API_COMPONENTS,
        "total_tags": len(API_TAGS),
        "metadata": API_METADATA
    }


def get_all_tags() -> List[str]:
    """Получение списка всех тегов API"""
    
    return [tag["name"] for tag in API_TAGS]


def get_health_status() -> Dict[str, Any]:
    """Базовая проверка состояния API компонентов"""
    
    return {
        "api_status": "healthy",
        "components": AVAILABLE_API_COMPONENTS,
        "version": __version__
    }


logger.info("FastAPI приложение инициализировано: %s", AVAILABLE_API_COMPONENTS)