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
from ..database import init_database_manager, DatabaseConfig, get_database_info
from ..core import get_version_info as get_core_version
from ..integrations import integration_manager

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
        if integration_manager:
            await integration_manager.disconnect_all()
        
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
    """
    📍 Регистрация всех роутов API
    
    Args:
        app: FastAPI приложение
    """
    
    # Базовые системные роуты
    @app.get("/", tags=["system"])
    async def root():
        """🏠 Корневой endpoint"""
        return {
            "message": "🤖 Avito AI Responder API",
            "version": __version__,
            "api_version": API_VERSION,
            "status": "running",
            "docs_url": f"/api/{API_VERSION}/docs"
        }
    
    @app.get("/health", tags=["system"])
    async def health_check():
        """🏥 Health check endpoint"""
        
        # Базовая проверка состояния
        health_status = {
            "status": "healthy",
            "version": __version__,
            "timestamp": time.time(),
            "components": {}
        }
        
        # Проверяем базу данных
        try:
            db_info = get_database_info()
            health_status["components"]["database"] = {
                "status": "healthy" if db_info["initialized"] else "not_initialized",
                "details": db_info
            }
        except Exception as e:
            health_status["components"]["database"] = {
                "status": "error", 
                "error": str(e)
            }
        
        # Проверяем ядро системы
        try:
            core_info = get_core_version()
            health_status["components"]["core"] = {
                "status": "healthy",
                "details": core_info
            }
        except Exception as e:
            health_status["components"]["core"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Проверяем интеграции
        try:
            if integration_manager:
                integration_status = await integration_manager.health_check_all()
                health_status["components"]["integrations"] = {
                    "status": "healthy" if all(integration_status.values()) else "partial",
                    "details": integration_status
                }
            else:
                health_status["components"]["integrations"] = {
                    "status": "not_initialized"
                }
        except Exception as e:
            health_status["components"]["integrations"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Определяем общий статус
        component_statuses = [
            comp["status"] for comp in health_status["components"].values()
        ]
        
        if any(status == "error" for status in component_statuses):
            health_status["status"] = "unhealthy"
        elif any(status in ["not_initialized", "partial"] for status in component_statuses):
            health_status["status"] = "degraded"
        
        return health_status
    
    @app.get("/info", tags=["system"])
    async def app_info():
        """ℹ️ Информация о приложении"""
        
        return {
            "app": API_METADATA,
            "version": __version__,
            "api_version": API_VERSION,
            "available_endpoints": len(API_TAGS),
            "environment": "development",  # TODO: Из переменных окружения
            "build_time": "2025-01-06T12:00:00Z",  # TODO: Из CI/CD
        }
    
    # TODO: Подключить роуты из modules
    # from .routes import auth_router, users_router, messages_router
    # app.include_router(auth_router, prefix=f"/api/{API_VERSION}")
    # app.include_router(users_router, prefix=f"/api/{API_VERSION}")
    # app.include_router(messages_router, prefix=f"/api/{API_VERSION}")
    
    logger.info("✅ Роуты зарегистрированы")


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