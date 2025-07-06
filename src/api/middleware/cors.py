"""
CORS middleware для FastAPI приложения.

Настройка Cross-Origin Resource Sharing для безопасного
взаимодействия фронтенда с API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import get_settings

settings = get_settings()


def setup_cors(app: FastAPI) -> None:
    """
    Настройка CORS middleware для FastAPI приложения.
    
    Конфигурирует разрешенные origins, методы и заголовки
    в зависимости от окружения (development/production).
    """
    # Базовые разрешенные origins
    allowed_origins = [
        "http://localhost:3000",  # React dev server
        "http://localhost:8000",  # FastAPI dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    
    # Добавляем дополнительные origins из настроек
    if settings.CORS_ORIGINS:
        origins_from_settings = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
        allowed_origins.extend(origins_from_settings)
    
    # В продакшене более строгие настройки
    if settings.ENVIRONMENT == "production":
        allowed_origins = [
            origin for origin in allowed_origins 
            if not origin.startswith("http://localhost") and not origin.startswith("http://127.0.0.1")
        ]
        # Добавляем продакшен домены
        allowed_origins.extend([
            "https://avito-ai-responder.com",
            "https://www.avito-ai-responder.com",
            "https://app.avito-ai-responder.com"
        ])
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Accept",
            "Accept-Language", 
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-API-Key",
            "Cache-Control"
        ],
        expose_headers=[
            "X-Total-Count",
            "X-Page-Count", 
            "X-Has-Next",
            "X-Has-Previous"
        ],
        max_age=600,  # 10 минут кеширования preflight запросов
    )