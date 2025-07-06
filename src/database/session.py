"""
🔄 Управление сессиями базы данных для Avito AI Responder

Этот модуль содержит утилиты для управления соединениями с БД:
- DatabaseManager - менеджер подключений
- get_db - dependency для FastAPI
- Контекстные менеджеры для транзакций
- Утилиты для работы с сессиями

Местоположение: src/database/session.py
"""

import logging
from contextlib import contextmanager, asynccontextmanager
from typing import Generator, AsyncGenerator, Optional, Dict, Any

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

from . import DatabaseConfig, engine, SessionLocal, Base

# Настройка логгера
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    🗄️ Менеджер базы данных
    
    Управляет подключениями, сессиями и транзакциями
    """
    
    def __init__(self, config: DatabaseConfig):
        """
        Инициализация менеджера БД
        
        Args:
            config: Конфигурация базы данных
        """
        self.config = config
        self.engine = None
        self.session_factory = None
        self.async_engine = None
        self.async_session_factory = None
        
        # Статистика
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "total_transactions": 0,
            "failed_transactions": 0,
            "total_queries": 0
        }
        
        logger.info("DatabaseManager инициализирован")
    
    def initialize_sync(self) -> bool:
        """
        Инициализация синхронного подключения
        
        Returns:
            bool: True если успешно
        """
        try:
            # Создаем движок
            self.engine = create_engine(
                self.config.database_url,
                **self.config.to_engine_kwargs(),
                poolclass=QueuePool,
                pool_pre_ping=True,  # Проверка соединений
                pool_recycle=self.config.pool_recycle
            )
            
            # Добавляем обработчики событий
            self._setup_event_listeners(self.engine)
            
            # Создаем фабрику сессий
            self.session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            
            # Тестируем подключение
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info("✅ Синхронное подключение к БД инициализировано")
            return True
            
        except Exception as e:
            logger.error("❌ Ошибка инициализации синхронного подключения: %s", e)
            return False
    
    def initialize_async(self) -> bool:
        """
        Инициализация асинхронного подключения
        
        Returns:
            bool: True если успешно
        """
        try:
            # Конвертируем URL для asyncpg
            async_url = self.config.database_url.replace(
                "postgresql://", "postgresql+asyncpg://"
            ).replace(
                "postgresql+psycopg2://", "postgresql+asyncpg://"
            )
            
            # Создаем асинхронный движок
            self.async_engine = create_async_engine(
                async_url,
                echo=self.config.echo,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle
            )
            
            # Создаем фабрику асинхронных сессий
            self.async_session_factory = async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            
            logger.info("✅ Асинхронное подключение к БД инициализировано")
            return True
            
        except Exception as e:
            logger.error("❌ Ошибка инициализации асинхронного подключения: %s", e)
            return False
    
    def _setup_event_listeners(self, engine) -> None:
        """Настройка обработчиков событий SQLAlchemy"""
        
        @event.listens_for(engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """Обработчик подключения"""
            self.stats["total_connections"] += 1
            self.stats["active_connections"] += 1
            logger.debug("Новое подключение к БД")
        
        @event.listens_for(engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            """Обработчик получения соединения из пула"""
            logger.debug("Соединение взято из пула")
        
        @event.listens_for(engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            """Обработчик возврата соединения в пул"""
            logger.debug("Соединение возвращено в пул")
        
        @event.listens_for(engine, "close")
        def on_close(dbapi_connection, connection_record):
            """Обработчик закрытия соединения"""
            self.stats["active_connections"] -= 1
            logger.debug("Соединение закрыто")
        
        @event.listens_for(engine, "before_cursor_execute")
        def on_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Обработчик перед выполнением запроса"""
            self.stats["total_queries"] += 1
            context._query_start_time = datetime.now()
        
        @event.listens_for(engine, "after_cursor_execute")
        def on_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Обработчик после выполнения запроса"""
            if hasattr(context, '_query_start_time'):
                from datetime import datetime
                execution_time = (datetime.now() - context._query_start_time).total_seconds()
                if execution_time > 1.0:  # Логируем медленные запросы
                    logger.warning("Медленный запрос (%.2fs): %s", execution_time, statement[:200])
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Контекстный менеджер для получения сессии
        
        Yields:
            Session: Сессия SQLAlchemy
        """
        if not self.session_factory:
            raise RuntimeError("БД не инициализирована")
        
        session = self.session_factory()
        try:
            yield session
        except Exception as e:
            logger.error("Ошибка в сессии БД: %s", e)
            session.rollback()
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Асинхронный контекстный менеджер для получения сессии
        
        Yields:
            AsyncSession: Асинхронная сессия SQLAlchemy
        """
        if not self.async_session_factory:
            raise RuntimeError("Асинхронная БД не инициализирована")
        
        session = self.async_session_factory()
        try:
            yield session
        except Exception as e:
            logger.error("Ошибка в асинхронной сессии БД: %s", e)
            await session.rollback()
            raise
        finally:
            await session.close()
    
    @contextmanager
    def transaction(self) -> Generator[Session, None, None]:
        """
        Контекстный менеджер для транзакций
        
        Yields:
            Session: Сессия с автоматическим управлением транзакциями
        """
        self.stats["total_transactions"] += 1
        
        with self.get_session() as session:
            try:
                session.begin()
                yield session
                session.commit()
                logger.debug("Транзакция зафиксирована")
            except Exception as e:
                self.stats["failed_transactions"] += 1
                session.rollback()
                logger.error("Транзакция отменена: %s", e)
                raise
    
    @asynccontextmanager
    async def async_transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Асинхронный контекстный менеджер для транзакций
        
        Yields:
            AsyncSession: Асинхронная сессия с управлением транзакциями
        """
        self.stats["total_transactions"] += 1
        
        async with self.get_async_session() as session:
            try:
                await session.begin()
                yield session
                await session.commit()
                logger.debug("Асинхронная транзакция зафиксирована")
            except Exception as e:
                self.stats["failed_transactions"] += 1
                await session.rollback()
                logger.error("Асинхронная транзакция отменена: %s", e)
                raise
    
    async def create_tables(self) -> bool:
        """
        Создание всех таблиц асинхронно
        
        Returns:
            bool: True если успешно
        """
        if not self.async_engine:
            logger.error("Асинхронный движок не инициализирован")
            return False
        
        try:
            async with self.async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("✅ Таблицы созданы асинхронно")
            return True
            
        except Exception as e:
            logger.error("❌ Ошибка создания таблиц: %s", e)
            return False
    
    async def drop_tables(self) -> bool:
        """
        Удаление всех таблиц асинхронно
        
        Returns:
            bool: True если успешно
        """
        if not self.async_engine:
            logger.error("Асинхронный движок не инициализирован")
            return False
        
        try:
            async with self.async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            
            logger.warning("⚠️ Все таблицы удалены асинхронно")
            return True
            
        except Exception as e:
            logger.error("❌ Ошибка удаления таблиц: %s", e)
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        Проверка состояния базы данных
        
        Returns:
            Dict[str, Any]: Статус и метрики БД
        """
        result = {
            "sync_engine": self.engine is not None,
            "async_engine": self.async_engine is not None,
            "stats": self.stats.copy()
        }
        
        # Проверяем синхронное подключение
        if self.engine:
            try:
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                result["sync_connection"] = True
            except Exception as e:
                result["sync_connection"] = False
                result["sync_error"] = str(e)
        
        # Добавляем информацию о пуле
        if self.engine and hasattr(self.engine.pool, 'size'):
            result["pool_info"] = {
                "size": self.engine.pool.size(),
                "checked_out": self.engine.pool.checkedout(),
                "overflow": self.engine.pool.overflow(),
                "checked_in": self.engine.pool.checkedin()
            }
        
        return result
    
    async def close(self) -> None:
        """Закрытие всех подключений"""
        
        if self.engine:
            self.engine.dispose()
            logger.info("Синхронный движок закрыт")
        
        if self.async_engine:
            await self.async_engine.dispose()
            logger.info("Асинхронный движок закрыт")


# Глобальный менеджер (будет инициализирован при запуске)
db_manager: Optional[DatabaseManager] = None


def init_database_manager(config: DatabaseConfig) -> DatabaseManager:
    """
    Инициализация глобального менеджера БД
    
    Args:
        config: Конфигурация базы данных
        
    Returns:
        DatabaseManager: Инициализированный менеджер
    """
    global db_manager
    
    db_manager = DatabaseManager(config)
    
    # Инициализируем синхронное подключение
    if not db_manager.initialize_sync():
        raise RuntimeError("Не удалось инициализировать синхронное подключение к БД")
    
    # Инициализируем асинхронное подключение
    if not db_manager.initialize_async():
        logger.warning("Не удалось инициализировать асинхронное подключение к БД")
    
    return db_manager


def get_db() -> Generator[Session, None, None]:
    """
    Dependency для FastAPI - получение сессии БД
    
    Yields:
        Session: Сессия SQLAlchemy
    """
    if not SessionLocal:
        raise RuntimeError("База данных не инициализирована")
    
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error("Ошибка в сессии БД: %s", e)
        db.rollback()
        raise
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для FastAPI - получение асинхронной сессии БД
    
    Yields:
        AsyncSession: Асинхронная сессия SQLAlchemy
    """
    if not db_manager or not db_manager.async_session_factory:
        raise RuntimeError("Асинхронная база данных не инициализирована")
    
    async with db_manager.get_async_session() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            logger.error("Ошибка в асинхронной сессии БД: %s", e)
            await session.rollback()
            raise


@contextmanager
def transaction() -> Generator[Session, None, None]:
    """
    Удобный контекстный менеджер для транзакций
    
    Yields:
        Session: Сессия с управлением транзакциями
    """
    if not db_manager:
        raise RuntimeError("Менеджер БД не инициализирован")
    
    with db_manager.transaction() as session:
        yield session


@asynccontextmanager
async def async_transaction() -> AsyncGenerator[AsyncSession, None]:
    """
    Удобный асинхронный контекстный менеджер для транзакций
    
    Yields:
        AsyncSession: Асинхронная сессия с управлением транзакциями
    """
    if not db_manager:
        raise RuntimeError("Менеджер БД не инициализирован")
    
    async with db_manager.async_transaction() as session:
        yield session


def execute_raw_sql(sql: str, params: Optional[Dict] = None) -> Any:
    """
    Выполнение сырого SQL запроса
    
    Args:
        sql: SQL запрос
        params: Параметры запроса
        
    Returns:
        Any: Результат выполнения
    """
    if not db_manager:
        raise RuntimeError("Менеджер БД не инициализирован")
    
    with db_manager.get_session() as session:
        result = session.execute(text(sql), params or {})
        return result.fetchall()


async def execute_raw_sql_async(sql: str, params: Optional[Dict] = None) -> Any:
    """
    Асинхронное выполнение сырого SQL запроса
    
    Args:
        sql: SQL запрос
        params: Параметры запроса
        
    Returns:
        Any: Результат выполнения
    """
    if not db_manager:
        raise RuntimeError("Менеджер БД не инициализирован")
    
    async with db_manager.get_async_session() as session:
        result = await session.execute(text(sql), params or {})
        return result.fetchall()


# Утилиты для работы с сессиями
class SessionContext:
    """Контекст для работы с сессиями"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def refresh_object(self, obj) -> None:
        """Обновление объекта из БД"""
        self.session.refresh(obj)
    
    def merge_object(self, obj):
        """Слияние объекта с сессией"""
        return self.session.merge(obj)
    
    def flush(self) -> None:
        """Принудительная отправка изменений в БД"""
        self.session.flush()


# Экспорт
__all__ = [
    # Основные классы
    "DatabaseManager",
    "SessionContext",
    
    # Функции
    "init_database_manager",
    "get_db",
    "get_async_db",
    "transaction",
    "async_transaction",
    "execute_raw_sql",
    "execute_raw_sql_async",
    
    # Глобальные объекты
    "db_manager"
]