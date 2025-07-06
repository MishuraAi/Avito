"""
🗄️ Пакет для работы с базой данных Avito AI Responder

Этот пакет содержит все компоненты для работы с PostgreSQL:
- models/    - SQLAlchemy модели данных
- crud/      - CRUD операции для работы с моделями
- session.py - Управление сессиями и соединениями
- config.py  - Конфигурация базы данных

Местоположение: src/database/__init__.py
"""

from typing import Optional, Dict, Any
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Настройка логгера
logger = logging.getLogger(__name__)

# Базовый класс для всех моделей
Base = declarative_base()

# Глобальные переменные для движка и сессий
engine = None
SessionLocal = None

# Будут импортироваться по мере создания
try:
    from .models import *
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False

try:
    from .crud import *
    CRUD_AVAILABLE = True
except ImportError:
    CRUD_AVAILABLE = False

try:
    from .session import DatabaseManager, get_db
    SESSION_AVAILABLE = True
except ImportError:
    SESSION_AVAILABLE = False


class DatabaseConfig:
    """Конфигурация базы данных"""
    
    def __init__(
        self,
        database_url: str,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        isolation_level: str = "READ_COMMITTED"
    ):
        """
        Инициализация конфигурации БД
        
        Args:
            database_url: URL подключения к PostgreSQL
            echo: Логировать SQL запросы
            pool_size: Размер пула соединений
            max_overflow: Максимальное переполнение пула
            pool_timeout: Таймаут получения соединения
            pool_recycle: Время переиспользования соединения (сек)
            isolation_level: Уровень изоляции транзакций
        """
        
        self.database_url = database_url
        self.echo = echo
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.isolation_level = isolation_level
    
    def validate(self) -> bool:
        """Валидация конфигурации"""
        
        if not self.database_url:
            return False
        
        if not self.database_url.startswith(('postgresql://', 'postgresql+psycopg2://')):
            return False
        
        if self.pool_size <= 0 or self.max_overflow < 0:
            return False
        
        return True
    
    def to_engine_kwargs(self) -> Dict[str, Any]:
        """Конвертация в аргументы для create_engine"""
        
        return {
            "echo": self.echo,
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
            "isolation_level": self.isolation_level
        }


def init_database(config: DatabaseConfig) -> bool:
    """
    Инициализация базы данных
    
    Args:
        config: Конфигурация подключения
        
    Returns:
        bool: True если инициализация успешна
    """
    
    global engine, SessionLocal
    
    try:
        if not config.validate():
            logger.error("Некорректная конфигурация базы данных")
            return False
        
        # Создаем движок
        engine = create_engine(
            config.database_url,
            **config.to_engine_kwargs()
        )
        
        # Добавляем обработчики событий для мониторинга
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Настройка соединения"""
            logger.debug("Новое соединение с БД установлено")
        
        @event.listens_for(engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Соединение взято из пула"""
            logger.debug("Соединение взято из пула")
        
        # Создаем фабрику сессий
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
        
        # Тестируем соединение
        with engine.connect() as conn:
            logger.info("✅ Подключение к базе данных успешно")
        
        return True
        
    except Exception as e:
        logger.error("❌ Ошибка инициализации базы данных: %s", e)
        return False


def create_tables() -> bool:
    """
    Создание всех таблиц в базе данных
    
    Returns:
        bool: True если создание успешно
    """
    
    global engine
    
    if not engine:
        logger.error("База данных не инициализирована")
        return False
    
    try:
        # Создаем все таблицы
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Таблицы базы данных созданы")
        return True
        
    except Exception as e:
        logger.error("❌ Ошибка создания таблиц: %s", e)
        return False


def drop_tables() -> bool:
    """
    Удаление всех таблиц (осторожно!)
    
    Returns:
        bool: True если удаление успешно
    """
    
    global engine
    
    if not engine:
        logger.error("База данных не инициализирована")
        return False
    
    try:
        Base.metadata.drop_all(bind=engine)
        logger.warning("⚠️ Все таблицы базы данных удалены")
        return True
        
    except Exception as e:
        logger.error("❌ Ошибка удаления таблиц: %s", e)
        return False


def get_database_info() -> Dict[str, Any]:
    """Получение информации о базе данных"""
    
    global engine, SessionLocal
    
    info = {
        "initialized": engine is not None,
        "session_factory": SessionLocal is not None,
        "available_components": {
            "models": MODELS_AVAILABLE,
            "crud": CRUD_AVAILABLE,
            "session": SESSION_AVAILABLE
        }
    }
    
    if engine:
        info.update({
            "url": str(engine.url).replace(str(engine.url.password), "***"),
            "pool_size": engine.pool.size(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
        })
    
    return info


def health_check() -> bool:
    """
    Проверка состояния базы данных
    
    Returns:
        bool: True если БД доступна
    """
    
    global engine
    
    if not engine:
        return False
    
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
        
    except Exception as e:
        logger.error("Health check БД неудачен: %s", e)
        return False


# Версия пакета базы данных
__version__ = "0.1.0"

# Экспортируемые компоненты
__all__ = [
    # Основные классы
    "Base",
    "DatabaseConfig",
    
    # Функции управления
    "init_database",
    "create_tables",
    "drop_tables",
    "get_database_info",
    "health_check",
    
    # Глобальные объекты
    "engine",
    "SessionLocal",
    
    # Информация о доступности
    "MODELS_AVAILABLE",
    "CRUD_AVAILABLE", 
    "SESSION_AVAILABLE",
    
    # Версия
    "__version__"
]

# Добавляем доступные компоненты в экспорт
if MODELS_AVAILABLE:
    __all__.extend([
        # Будут добавлены при создании моделей
    ])

if CRUD_AVAILABLE:
    __all__.extend([
        # Будут добавлены при создании CRUD
    ])

if SESSION_AVAILABLE:
    __all__.extend([
        "DatabaseManager",
        "get_db"
    ])