"""
📋 Pydantic схемы для API Avito AI Responder

Этот пакет содержит все Pydantic схемы для валидации API:
- base.py      - Базовые схемы и миксины
- auth.py      - Схемы аутентификации
- users.py     - Схемы пользователей и продавцов
- messages.py  - Схемы сообщений и диалогов
- responses.py - Стандартные ответы API

Местоположение: src/api/schemas/__init__.py
"""

from typing import Dict, Any, List
import logging

# Настройка логгера
logger = logging.getLogger(__name__)

# Будут импортироваться по мере создания
try:
    from .base import BaseSchema, PaginatedResponse, ErrorResponse, SuccessResponse
    BASE_SCHEMAS_AVAILABLE = True
except ImportError:
    BASE_SCHEMAS_AVAILABLE = False

try:
    from .auth import LoginRequest, LoginResponse, TokenResponse, RegisterRequest
    AUTH_SCHEMAS_AVAILABLE = True
except ImportError:
    AUTH_SCHEMAS_AVAILABLE = False

try:
    from .users import (
        UserResponse, UserCreate, UserUpdate,
        SellerResponse, SellerCreate, SellerUpdate,
        UserProfileResponse, SellerSettingsResponse
    )
    USER_SCHEMAS_AVAILABLE = True
except ImportError:
    USER_SCHEMAS_AVAILABLE = False

try:
    from .messages import (
        MessageResponse, MessageCreate, MessageUpdate,
        ConversationResponse, ConversationCreate, ConversationUpdate,
        MessageTemplateResponse, MessageTemplateCreate
    )
    MESSAGE_SCHEMAS_AVAILABLE = True
except ImportError:
    MESSAGE_SCHEMAS_AVAILABLE = False

try:
    from .responses import APIResponse, ErrorDetails, ValidationError
    RESPONSE_SCHEMAS_AVAILABLE = True
except ImportError:
    RESPONSE_SCHEMAS_AVAILABLE = False


# Информация о доступности схем
AVAILABLE_SCHEMAS = {
    "base": BASE_SCHEMAS_AVAILABLE,
    "auth": AUTH_SCHEMAS_AVAILABLE,
    "users": USER_SCHEMAS_AVAILABLE,
    "messages": MESSAGE_SCHEMAS_AVAILABLE,
    "responses": RESPONSE_SCHEMAS_AVAILABLE
}

# Версия схем
__version__ = "1.0.0"

# Экспортируемые компоненты
__all__ = [
    # Информация о доступности
    "AVAILABLE_SCHEMAS",
    "__version__"
]

# Добавляем базовые схемы если доступны
if BASE_SCHEMAS_AVAILABLE:
    __all__.extend([
        "BaseSchema",
        "PaginatedResponse",
        "ErrorResponse", 
        "SuccessResponse"
    ])

# Добавляем схемы аутентификации если доступны
if AUTH_SCHEMAS_AVAILABLE:
    __all__.extend([
        "LoginRequest",
        "LoginResponse",
        "TokenResponse",
        "RegisterRequest"
    ])

# Добавляем схемы пользователей если доступны
if USER_SCHEMAS_AVAILABLE:
    __all__.extend([
        "UserResponse",
        "UserCreate", 
        "UserUpdate",
        "SellerResponse",
        "SellerCreate",
        "SellerUpdate",
        "UserProfileResponse",
        "SellerSettingsResponse"
    ])

# Добавляем схемы сообщений если доступны
if MESSAGE_SCHEMAS_AVAILABLE:
    __all__.extend([
        "MessageResponse",
        "MessageCreate",
        "MessageUpdate", 
        "ConversationResponse",
        "ConversationCreate",
        "ConversationUpdate",
        "MessageTemplateResponse",
        "MessageTemplateCreate"
    ])

# Добавляем схемы ответов если доступны
if RESPONSE_SCHEMAS_AVAILABLE:
    __all__.extend([
        "APIResponse",
        "ErrorDetails",
        "ValidationError"
    ])


def get_schemas_info() -> Dict[str, Any]:
    """Получение информации о доступных схемах"""
    
    return {
        "version": __version__,
        "available_schemas": AVAILABLE_SCHEMAS,
        "total_schema_modules": len(AVAILABLE_SCHEMAS),
        "schema_categories": {
            "base": ["BaseSchema", "PaginatedResponse", "ErrorResponse", "SuccessResponse"] if BASE_SCHEMAS_AVAILABLE else [],
            "auth": ["LoginRequest", "LoginResponse", "TokenResponse", "RegisterRequest"] if AUTH_SCHEMAS_AVAILABLE else [],
            "users": ["UserResponse", "SellerResponse", "UserProfileResponse", "SellerSettingsResponse"] if USER_SCHEMAS_AVAILABLE else [],
            "messages": ["MessageResponse", "ConversationResponse", "MessageTemplateResponse"] if MESSAGE_SCHEMAS_AVAILABLE else [],
            "responses": ["APIResponse", "ErrorDetails", "ValidationError"] if RESPONSE_SCHEMAS_AVAILABLE else []
        }
    }


def get_all_schemas() -> List[str]:
    """Получение списка всех доступных схем"""
    
    schemas = []
    
    if BASE_SCHEMAS_AVAILABLE:
        schemas.extend(["BaseSchema", "PaginatedResponse", "ErrorResponse", "SuccessResponse"])
    
    if AUTH_SCHEMAS_AVAILABLE:
        schemas.extend(["LoginRequest", "LoginResponse", "TokenResponse", "RegisterRequest"])
    
    if USER_SCHEMAS_AVAILABLE:
        schemas.extend([
            "UserResponse", "UserCreate", "UserUpdate",
            "SellerResponse", "SellerCreate", "SellerUpdate", 
            "UserProfileResponse", "SellerSettingsResponse"
        ])
    
    if MESSAGE_SCHEMAS_AVAILABLE:
        schemas.extend([
            "MessageResponse", "MessageCreate", "MessageUpdate",
            "ConversationResponse", "ConversationCreate", "ConversationUpdate",
            "MessageTemplateResponse", "MessageTemplateCreate"
        ])
    
    if RESPONSE_SCHEMAS_AVAILABLE:
        schemas.extend(["APIResponse", "ErrorDetails", "ValidationError"])
    
    return schemas


logger.info("API схемы инициализированы: %s", AVAILABLE_SCHEMAS)