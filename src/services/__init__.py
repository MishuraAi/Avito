"""
Сервисный слой для Авито ИИ-бота.

Этот модуль содержит всю бизнес-логику приложения, обеспечивая
чистую архитектуру между API роутами и данными.
"""

from .auth_service import AuthService
from .user_service import UserService
from .message_service import MessageService
from .avito_service import AvitoService

__all__ = [
    "AuthService",
    "UserService", 
    "MessageService",
    "AvitoService"
]