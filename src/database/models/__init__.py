"""
📋 Модели данных для Avito AI Responder

Этот пакет содержит все SQLAlchemy модели:
- base.py      - Базовая модель с общими полями
- users.py     - Модели пользователей и продавцов
- messages.py  - Модели сообщений и диалогов
- products.py  - Модели товаров и объявлений
- settings.py  - Модели настроек системы
- analytics.py - Модели для аналитики и метрик

Местоположение: src/database/models/__init__.py
"""

from typing import List, Dict, Any
import logging

# Настройка логгера
logger = logging.getLogger(__name__)

# Импортируем базовые классы
try:
    from .base import Base, BaseModel, TimestampMixin
    BASE_AVAILABLE = True
except ImportError:
    BASE_AVAILABLE = False

# Будут импортироваться по мере создания
try:
    from .users import User, Seller, UserProfile
    USERS_AVAILABLE = True
except ImportError:
    USERS_AVAILABLE = False

try:
    from .messages import Message, Conversation, MessageTemplate
    MESSAGES_AVAILABLE = True
except ImportError:
    MESSAGES_AVAILABLE = False

try:
    from .products import Product, ProductImage, ProductCategory
    PRODUCTS_AVAILABLE = True
except ImportError:
    PRODUCTS_AVAILABLE = False

try:
    from .settings import SystemSettings, UserSettings, IntegrationSettings
    SETTINGS_AVAILABLE = True
except ImportError:
    SETTINGS_AVAILABLE = False

try:
    from .analytics import MessageAnalytics, ConversationMetrics, SystemMetrics
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False


# Информация о доступности моделей
AVAILABLE_MODELS = {
    "base": BASE_AVAILABLE,
    "users": USERS_AVAILABLE,
    "messages": MESSAGES_AVAILABLE,
    "products": PRODUCTS_AVAILABLE,
    "settings": SETTINGS_AVAILABLE,
    "analytics": ANALYTICS_AVAILABLE
}

# Версия моделей
__version__ = "0.1.0"

# Экспортируемые компоненты
__all__ = [
    # Информация о доступности
    "AVAILABLE_MODELS",
    "__version__"
]

# Добавляем базовые компоненты если доступны
if BASE_AVAILABLE:
    __all__.extend([
        "Base",  # ВАЖНО: Добавляем Base для миграций!
        "BaseModel",
        "TimestampMixin"
    ])

# Добавляем модели пользователей если доступны
if USERS_AVAILABLE:
    __all__.extend([
        "User",
        "Seller", 
        "UserProfile"
    ])

# Добавляем модели сообщений если доступны
if MESSAGES_AVAILABLE:
    __all__.extend([
        "Message",
        "Conversation",
        "MessageTemplate"
    ])

# Добавляем модели продуктов если доступны
if PRODUCTS_AVAILABLE:
    __all__.extend([
        "Product",
        "ProductImage",
        "ProductCategory"
    ])

# Добавляем модели настроек если доступны
if SETTINGS_AVAILABLE:
    __all__.extend([
        "SystemSettings",
        "UserSettings",
        "IntegrationSettings"
    ])

# Добавляем модели аналитики если доступны
if ANALYTICS_AVAILABLE:
    __all__.extend([
        "MessageAnalytics",
        "ConversationMetrics",
        "SystemMetrics"
    ])


def get_all_models() -> List[str]:
    """Получение списка всех доступных моделей"""
    
    models = []
    
    if BASE_AVAILABLE:
        models.extend(["Base", "BaseModel", "TimestampMixin"])
    
    if USERS_AVAILABLE:
        models.extend(["User", "Seller", "UserProfile"])
    
    if MESSAGES_AVAILABLE:
        models.extend(["Message", "Conversation", "MessageTemplate"])
    
    if PRODUCTS_AVAILABLE:
        models.extend(["Product", "ProductImage", "ProductCategory"])
    
    if SETTINGS_AVAILABLE:
        models.extend(["SystemSettings", "UserSettings", "IntegrationSettings"])
    
    if ANALYTICS_AVAILABLE:
        models.extend(["MessageAnalytics", "ConversationMetrics", "SystemMetrics"])
    
    return models


def get_models_info() -> Dict[str, Any]:
    """Получение детальной информации о моделях"""
    
    return {
        "version": __version__,
        "available_models": AVAILABLE_MODELS,
        "total_models": len(get_all_models()),
        "model_categories": {
            "base": ["Base", "BaseModel", "TimestampMixin"] if BASE_AVAILABLE else [],
            "users": ["User", "Seller", "UserProfile"] if USERS_AVAILABLE else [],
            "messages": ["Message", "Conversation", "MessageTemplate"] if MESSAGES_AVAILABLE else [],
            "products": ["Product", "ProductImage", "ProductCategory"] if PRODUCTS_AVAILABLE else [],
            "settings": ["SystemSettings", "UserSettings", "IntegrationSettings"] if SETTINGS_AVAILABLE else [],
            "analytics": ["MessageAnalytics", "ConversationMetrics", "SystemMetrics"] if ANALYTICS_AVAILABLE else []
        }
    }


logger.info("Модели базы данных инициализированы: %s", AVAILABLE_MODELS)