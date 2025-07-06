"""
Утилиты для Авито ИИ-бота.

Этот модуль содержит вспомогательные функции, валидаторы,
форматтеры и кастомные исключения.
"""

from .exceptions import (
    BaseAppException,
    ValidationError,
    BusinessLogicError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ExternalServiceError
)

from .validators import (
    validate_email,
    validate_phone,
    validate_message_content,
    validate_avito_credentials
)

from .formatters import (
    format_user_activity,
    format_seller_stats,
    format_message_for_ai,
    format_ai_response,
    format_avito_message,
    format_avito_listing
)

from .helpers import (
    generate_unique_id,
    sanitize_html,
    truncate_text,
    parse_phone_number,
    calculate_text_similarity
)

__all__ = [
    # Исключения
    "BaseAppException",
    "ValidationError", 
    "BusinessLogicError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ExternalServiceError",
    
    # Валидаторы
    "validate_email",
    "validate_phone",
    "validate_message_content",
    "validate_avito_credentials",
    
    # Форматтеры
    "format_user_activity",
    "format_seller_stats", 
    "format_message_for_ai",
    "format_ai_response",
    "format_avito_message",
    "format_avito_listing",
    
    # Помощники
    "generate_unique_id",
    "sanitize_html",
    "truncate_text",
    "parse_phone_number",
    "calculate_text_similarity"
]