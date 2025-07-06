"""
🧪 Конфигурация pytest для Avito AI Bot

Этот файл содержит:
- Фикстуры для тестов
- Настройки тестовой среды
- Общие утилиты для тестирования
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Generator, AsyncGenerator
from unittest.mock import Mock, AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import get_settings
from src.database.models import Base
from src.database.session import DatabaseManager
from src.api.main import app


# ============================================================================
# 🔧 НАСТРОЙКИ ТЕСТОВОЙ СРЕДЫ
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Настройка тестовой среды"""
    # Устанавливаем переменные окружения для тестов
    os.environ["TESTING"] = "True"
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"
    os.environ["REDIS_URL"] = "redis://localhost:6379/15"  # Тестовая БД Redis
    
    yield
    
    # Очистка после всех тестов
    test_db_path = Path("./test.db")
    if test_db_path.exists():
        test_db_path.unlink()


# ============================================================================
# 🗄️ ФИКСТУРЫ ДЛЯ БАЗЫ ДАННЫХ
# ============================================================================

@pytest.fixture(scope="session")
def test_engine():
    """Создать тестовый движок SQLAlchemy"""
    engine = create_engine(
        "sqlite:///./test.db",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    # Создаем все таблицы
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Удаляем все таблицы после тестов
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def test_db_session(test_engine):
    """Создать тестовую сессию базы данных"""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
async def async_test_db_session(test_engine):
    """Создать асинхронную тестовую сессию"""
    # Для тестов используем синхронную сессию как асинхронную
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ============================================================================
# 🌐 ФИКСТУРЫ ДЛЯ API
# ============================================================================

@pytest.fixture
def test_client(test_db_session):
    """Создать тестовый клиент FastAPI"""
    
    # Переопределяем зависимость базы данных
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass
    
    from src.api.dependencies import get_db
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    # Очищаем переопределения после теста
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(test_client):
    """Создать заголовки аутентификации для тестов"""
    # Создаем тестового пользователя и получаем токен
    user_data = {
        "email": "test@example.com",
        "password": "testpassword123",
        "first_name": "Test",
        "last_name": "User"
    }
    
    # Регистрируем пользователя
    response = test_client.post("/api/auth/register", json=user_data)
    
    if response.status_code == 201:
        # Логинимся
        login_data = {"email": user_data["email"], "password": user_data["password"]}
        response = test_client.post("/api/auth/login", json=login_data)
        
        if response.status_code == 200:
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}
    
    return {}


# ============================================================================
# 🤖 МОКИРОВАННЫЕ ВНЕШНИЕ СЕРВИСЫ
# ============================================================================

@pytest.fixture
def mock_gemini_client():
    """Мокированный клиент Gemini API"""
    mock = AsyncMock()
    mock.generate_response.return_value = {
        "content": "Тестовый ответ от ИИ",
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        "model": "gemini-pro"
    }
    return mock


@pytest.fixture
def mock_avito_client():
    """Мокированный клиент Avito API"""
    mock = AsyncMock()
    mock.get_messages.return_value = [
        {
            "id": "msg_123",
            "content": "Тестовое сообщение",
            "created_at": "2025-01-06T12:00:00Z",
            "author": {"id": "user_456", "name": "Test User"}
        }
    ]
    mock.send_message.return_value = {"id": "msg_789", "status": "sent"}
    return mock


# ============================================================================
# 📊 ФИКСТУРЫ ДЛЯ ТЕСТОВЫХ ДАННЫХ
# ============================================================================

@pytest.fixture
def sample_user_data():
    """Тестовые данные пользователя"""
    return {
        "email": "user@example.com",
        "password": "securepassword123",
        "first_name": "John",
        "last_name": "Doe",
        "phone": "+7900123456"
    }


@pytest.fixture
def sample_seller_data():
    """Тестовые данные продавца"""
    return {
        "email": "seller@example.com",
        "password": "sellerpassword123",
        "first_name": "Jane",
        "last_name": "Smith",
        "company_name": "Test Company",
        "avito_user_id": "avito_123"
    }


@pytest.fixture
def sample_message_data():
    """Тестовые данные сообщения"""
    return {
        "content": "Здравствуйте! Интересует ваш товар. Можно узнать подробности?",
        "message_type": "incoming",
        "platform": "avito",
        "external_message_id": "ext_msg_123"
    }


# ============================================================================
# 🔧 УТИЛИТЫ ДЛЯ ТЕСТОВ
# ============================================================================

@pytest.fixture
def create_test_user(test_db_session):
    """Фабрика для создания тестовых пользователей"""
    def _create_user(**kwargs):
        from src.database.models.users import User
        from src.utils.helpers import hash_password
        
        default_data = {
            "email": "test@example.com",
            "password_hash": hash_password("password123"),
            "first_name": "Test",
            "last_name": "User",
            "is_active": True
        }
        default_data.update(kwargs)
        
        user = User(**default_data)
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)
        
        return user
    
    return _create_user


@pytest.fixture
def create_test_seller(test_db_session):
    """Фабрика для создания тестовых продавцов"""
    def _create_seller(**kwargs):
        from src.database.models.users import Seller
        from src.utils.helpers import hash_password
        
        default_data = {
            "email": "seller@example.com",
            "password_hash": hash_password("password123"),
            "first_name": "Test",
            "last_name": "Seller",
            "company_name": "Test Company",
            "is_active": True,
            "subscription_type": "free"
        }
        default_data.update(kwargs)
        
        seller = Seller(**default_data)
        test_db_session.add(seller)
        test_db_session.commit()
        test_db_session.refresh(seller)
        
        return seller
    
    return _create_seller


# ============================================================================
# ⚡ ASYNC UTILITIES
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Создать event loop для async тестов"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# 🏷️ МАРКЕРЫ ДЛЯ ПРОПУСКА ТЕСТОВ
# ============================================================================

def pytest_configure(config):
    """Конфигурация pytest"""
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Модификация коллекции тестов"""
    # Пропускаем external тесты если нет соответствующих API ключей
    skip_external = pytest.mark.skip(reason="External API keys not configured")
    
    for item in items:
        if "external" in item.keywords:
            settings = get_settings()
            if not settings.gemini_api_key or settings.gemini_api_key == "your-gemini-api-key-here":
                item.add_marker(skip_external)


# ============================================================================
# 📝 ЛОГИРОВАНИЕ ДЛЯ ТЕСТОВ
# ============================================================================

@pytest.fixture(autouse=True)
def configure_test_logging(caplog):
    """Настройка логирования для тестов"""
    import logging
    
    # Устанавливаем уровень логирования для тестов
    logging.getLogger("src").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.ERROR)
    
    yield caplog


# ============================================================================
# 🧹 ОЧИСТКА ПОСЛЕ ТЕСТОВ
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Автоматическая очистка после каждого теста"""
    yield
    
    # Очищаем кеши, временные файлы и т.д.
    import gc
    gc.collect()