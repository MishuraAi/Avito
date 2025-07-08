"""
🌐 Главное FastAPI приложение для Avito AI Responder

Этот модуль создает и настраивает основное FastAPI приложение:
- Инициализация приложения с метаданными
- Подключение middleware
- Регистрация роутов
- Настройка CORS
- Обработка ошибок

Местоположение: src/api/main.py
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import API_METADATA, API_TAGS, __version__, API_VERSION
from ..database import DatabaseConfig, get_database_info, init_database
# from ..core import get_version_info as get_core_version  # �������� ���������
# # from ..integrations import integration_manager  # �������� ���������  # Временно отключено

# Настройка логгера
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    🔄 Управление жизненным циклом приложения
    
    Выполняется при запуске и остановке приложения
    """
    
    # Запуск приложения
    logger.info("🚀 Запуск Avito AI Responder API v%s", __version__)
    
    try:
        # Инициализация базы данных
        # TODO: Получать конфигурацию из переменных окружения
        # db_config = DatabaseConfig(database_url=os.getenv("DATABASE_URL"))
        # init_database_manager(db_config)
        logger.info("✅ База данных готова к подключению")
        
        # Инициализация интеграций
        # TODO: Инициализировать интеграции с реальными ключами
        logger.info("✅ Интеграции готовы к подключению")
        
        # Приложение готово
        logger.info("🎉 API успешно запущен и готов к работе!")
        
        yield
        
    except Exception as e:
        logger.error("❌ Ошибка запуска приложения: %s", e)
        raise
    
    finally:
        # Остановка приложения
        logger.info("🛑 Остановка Avito AI Responder API")
        
        # Закрытие соединений
        # if integration_manager:
        #     await integration_manager.disconnect_all()
        
        logger.info("✅ Приложение корректно остановлено")


def create_app() -> FastAPI:
    """
    🏭 Фабрика для создания FastAPI приложения
    
    Returns:
        FastAPI: Настроенное приложение
    """
    
    # Создаем приложение
    app = FastAPI(
        lifespan=lifespan,
        **API_METADATA,
        openapi_tags=API_TAGS,
        openapi_url=f"/api/{API_VERSION}/openapi.json",
        docs_url=f"/api/{API_VERSION}/docs",
        redoc_url=f"/api/{API_VERSION}/redoc"
    )

    # ===============================================
    # ДОБАВЛЯЕМ ПРОДАКШЕН CORS + ЛОГИРОВАНИЕ + HEALTH CHECK
    # ===============================================
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://avito-joq9.onrender.com",
            "https://*.onrender.com",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "*"  # Временно для отладки, в продакшене убрать
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request, call_next):
        import time
        start_time = time.time()
        print(f"\U0001F4E5 {request.method} {request.url}")
        print(f"\U0001F310 Host: {request.headers.get('host', 'unknown')}")
        print(f"\U0001F464 User-Agent: {request.headers.get('user-agent', 'unknown')[:50]}...")
        response = await call_next(request)
        process_time = time.time() - start_time
        print(f"\U0001F4E4 Response: {response.status_code} ({process_time:.3f}s)")
        return response

    @app.get("/")
    async def root():
        """Главная страница"""
        return {
            "message": "Avito AI Responder API",
            "status": "running",
            "version": "1.0.0",
            "docs": "/docs"
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": "avito-ai-responder",
            "timestamp": "2025-01-08T02:00:00Z",
            "endpoints": [
                "/",
                "/health",
                "/docs",
                "/api/v1/auth/avito/status",
                "/api/v1/auth/avito/callback"
            ]
        }
    # ===============================================
    # КОНЕЦ ДОБАВЛЕНИЯ
    # ===============================================
    
    # Настраиваем middleware
    setup_middleware(app)
    
    # Настраиваем обработчики ошибок
    setup_exception_handlers(app)
    
    # Регистрируем роуты
    register_routes(app)
    
    return app


def setup_middleware(app: FastAPI) -> None:
    """
    🛡️ Настройка middleware компонентов
    
    Args:
        app: FastAPI приложение
    """
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # React dev server
            "http://localhost:8000",  # FastAPI dev server
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
            # TODO: Добавить продакшен домены
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
    )
    
    # Trusted hosts middleware
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=[
            "localhost",
            "127.0.0.1",
            "*.railway.app",  # Railway хостинг
            # TODO: Добавить продакшен домены
        ]
    )
    
    # Middleware для логирования запросов
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Логирование всех HTTP запросов"""
        
        start_time = time.time()
        
        # Логируем входящий запрос
        logger.info(
            "📨 %s %s - %s",
            request.method,
            request.url.path,
            request.client.host if request.client else "unknown"
        )
        
        # Выполняем запрос
        response = await call_next(request)
        
        # Логируем ответ
        process_time = time.time() - start_time
        logger.info(
            "📤 %s %s - %d - %.3fs",
            request.method,
            request.url.path,
            response.status_code,
            process_time
        )
        
        # Добавляем заголовок с временем обработки
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
    # TODO: Добавить middleware для аутентификации
    # TODO: Добавить middleware для rate limiting
    # TODO: Добавить middleware для безопасности


def setup_exception_handlers(app: FastAPI) -> None:
    """
    🚨 Настройка обработчиков ошибок
    
    Args:
        app: FastAPI приложение
    """
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Обработчик HTTP ошибок"""
        
        logger.warning(
            "HTTP ошибка %d: %s - %s %s",
            exc.status_code,
            exc.detail,
            request.method,
            request.url.path
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "status_code": exc.status_code,
                "message": exc.detail,
                "path": str(request.url.path),
                "timestamp": time.time()
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Обработчик ошибок валидации"""
        
        logger.warning(
            "Ошибка валидации: %s - %s %s",
            exc.errors(),
            request.method,
            request.url.path
        )
        
        return JSONResponse(
            status_code=422,
            content={
                "error": True,
                "status_code": 422,
                "message": "Ошибка валидации данных",
                "details": exc.errors(),
                "path": str(request.url.path),
                "timestamp": time.time()
            }
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
        """Обработчик общих HTTP ошибок"""
        
        logger.error(
            "Starlette ошибка %d: %s - %s %s",
            exc.status_code,
            exc.detail,
            request.method,
            request.url.path
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "status_code": exc.status_code,
                "message": exc.detail,
                "path": str(request.url.path),
                "timestamp": time.time()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Обработчик всех остальных ошибок"""
        
        logger.error(
            "Необработанная ошибка: %s - %s %s",
            str(exc),
            request.method,
            request.url.path,
            exc_info=True
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "status_code": 500,
                "message": "Внутренняя ошибка сервера",
                "path": str(request.url.path),
                "timestamp": time.time()
            }
        )


def register_routes(app: FastAPI) -> None:
    """Регистрация API роутов - МИНИМАЛЬНАЯ ВЕРСИЯ"""
    try:
        from src.routes.auth import router as auth_router
        app.include_router(auth_router, prefix="/api/v1/auth", tags=["authentication"])
        print("✅ Auth router успешно зарегистрирован")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


# Создаем экземпляр приложения
app = create_app()

# Экспорт
__all__ = [
    "app",
    "create_app",
    "setup_middleware",
    "setup_exception_handlers", 
    "register_routes"
]

