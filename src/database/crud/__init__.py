"""
📋 CRUD операции для Avito AI Responder

Этот пакет содержит все CRUD операции для работы с моделями:
- base.py         - Базовый CRUD класс с общими операциями
- users.py        - CRUD для пользователей и продавцов
- messages.py     - CRUD для сообщений и шаблонов
- conversations.py - CRUD для диалогов

Местоположение: src/database/crud/__init__.py
"""

from typing import Dict, Any, List
import logging

# Настройка логгера
logger = logging.getLogger(__name__)

# Будут импортироваться по мере создания
try:
    from .base import BaseCRUD
    BASE_CRUD_AVAILABLE = True
except ImportError:
    BASE_CRUD_AVAILABLE = False

try:
    from .users import UserCRUD, SellerCRUD, UserProfileCRUD, SellerSettingsCRUD
    USER_CRUD_AVAILABLE = True
except ImportError:
    USER_CRUD_AVAILABLE = False

try:
    from .messages import MessageCRUD, MessageTemplateCRUD
    MESSAGE_CRUD_AVAILABLE = True
except ImportError:
    MESSAGE_CRUD_AVAILABLE = False

try:
    from .conversations import ConversationCRUD
    CONVERSATION_CRUD_AVAILABLE = True
except ImportError:
    CONVERSATION_CRUD_AVAILABLE = False


# Информация о доступности CRUD операций
AVAILABLE_CRUD = {
    "base": BASE_CRUD_AVAILABLE,
    "users": USER_CRUD_AVAILABLE,
    "messages": MESSAGE_CRUD_AVAILABLE,
    "conversations": CONVERSATION_CRUD_AVAILABLE
}

# Версия CRUD пакета
__version__ = "0.1.0"

# Экспортируемые компоненты
__all__ = [
    # Информация о доступности
    "AVAILABLE_CRUD",
    "__version__"
]

# Добавляем базовые CRUD если доступны
if BASE_CRUD_AVAILABLE:
    __all__.extend([
        "BaseCRUD"
    ])

# Добавляем CRUD пользователей если доступны
if USER_CRUD_AVAILABLE:
    __all__.extend([
        "UserCRUD",
        "SellerCRUD",
        "UserProfileCRUD", 
        "SellerSettingsCRUD"
    ])

# Добавляем CRUD сообщений если доступны
if MESSAGE_CRUD_AVAILABLE:
    __all__.extend([
        "MessageCRUD",
        "MessageTemplateCRUD"
    ])

# Добавляем CRUD диалогов если доступны
if CONVERSATION_CRUD_AVAILABLE:
    __all__.extend([
        "ConversationCRUD"
    ])


def get_crud_info() -> Dict[str, Any]:
    """Получение информации о доступных CRUD операциях"""
    
    return {
        "version": __version__,
        "available_crud": AVAILABLE_CRUD,
        "total_crud_classes": len(__all__) - 2,  # Исключаем служебные поля
        "crud_categories": {
            "base": ["BaseCRUD"] if BASE_CRUD_AVAILABLE else [],
            "users": ["UserCRUD", "SellerCRUD", "UserProfileCRUD", "SellerSettingsCRUD"] if USER_CRUD_AVAILABLE else [],
            "messages": ["MessageCRUD", "MessageTemplateCRUD"] if MESSAGE_CRUD_AVAILABLE else [],
            "conversations": ["ConversationCRUD"] if CONVERSATION_CRUD_AVAILABLE else []
        }
    }


def get_all_crud_classes() -> List[str]:
    """Получение списка всех доступных CRUD классов"""
    
    crud_classes = []
    
    if BASE_CRUD_AVAILABLE:
        crud_classes.extend(["BaseCRUD"])
    
    if USER_CRUD_AVAILABLE:
        crud_classes.extend(["UserCRUD", "SellerCRUD", "UserProfileCRUD", "SellerSettingsCRUD"])
    
    if MESSAGE_CRUD_AVAILABLE:
        crud_classes.extend(["MessageCRUD", "MessageTemplateCRUD"])
    
    if CONVERSATION_CRUD_AVAILABLE:
        crud_classes.extend(["ConversationCRUD"])
    
    return crud_classes


def get_crud_status() -> Dict[str, Any]:
    """Получение детального статуса CRUD операций"""
    
    status = {
        "initialized": True,
        "available_modules": [],
        "missing_modules": [],
        "total_classes": len(get_all_crud_classes())
    }
    
    for module_name, is_available in AVAILABLE_CRUD.items():
        if is_available:
            status["available_modules"].append(module_name)
        else:
            status["missing_modules"].append(module_name)
    
    return status


# Создаем экземпляры CRUD для удобного использования
def create_crud_instances():
    """Создание экземпляров CRUD для быстрого использования"""
    instances = {}
    
    try:
        if BASE_CRUD_AVAILABLE:
            # BaseCRUD - абстрактный класс, экземпляр не создаем
            pass
        
        if USER_CRUD_AVAILABLE:
            instances['user_crud'] = UserCRUD()
            instances['seller_crud'] = SellerCRUD()
            instances['user_profile_crud'] = UserProfileCRUD()
            instances['seller_settings_crud'] = SellerSettingsCRUD()
        
        if MESSAGE_CRUD_AVAILABLE:
            instances['message_crud'] = MessageCRUD()
            instances['message_template_crud'] = MessageTemplateCRUD()
        
        if CONVERSATION_CRUD_AVAILABLE:
            instances['conversation_crud'] = ConversationCRUD()
        
        logger.info(f"Создано {len(instances)} экземпляров CRUD")
        
    except Exception as e:
        logger.error(f"Ошибка создания экземпляров CRUD: {e}")
        instances = {}
    
    return instances


# Глобальные экземпляры CRUD (создаются при импорте)
try:
    CRUD_INSTANCES = create_crud_instances()
    CRUD_INSTANCES_AVAILABLE = True
except Exception as e:
    logger.warning(f"Не удалось создать экземпляры CRUD: {e}")
    CRUD_INSTANCES = {}
    CRUD_INSTANCES_AVAILABLE = False

# Добавляем информацию об экземплярах в экспорт
__all__.extend([
    "get_crud_info",
    "get_all_crud_classes", 
    "get_crud_status",
    "create_crud_instances",
    "CRUD_INSTANCES",
    "CRUD_INSTANCES_AVAILABLE"
])

logger.info("CRUD операции инициализированы: %s", AVAILABLE_CRUD)
logger.info("Создано экземпляров CRUD: %s", len(CRUD_INSTANCES) if CRUD_INSTANCES_AVAILABLE else 0)