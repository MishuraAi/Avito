"""
🔄 Конфигурация Alembic для миграций базы данных
Avito AI Responder - автоматически сгенерировано

Поддерживает:
- SQLite и PostgreSQL
- Автоматическое получение URL из настроек
- Корректный импорт моделей
- Обработка ошибок
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys
from pathlib import Path

# Добавляем корневую папку проекта в путь для импорта
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Импортируем настройки и модели
try:
    from src.core.config import get_settings
    from src.database.models import Base
except ImportError as e:
    print(f"❌ Ошибка импорта в env.py: {e}")
    print("📝 Убедитесь что структура проекта корректна")
    sys.exit(1)

# Конфигурация Alembic
config = context.config

# Интерпретируем конфигурационный файл для логирования
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Устанавливаем target_metadata для автогенерации
target_metadata = Base.metadata

def get_url():
    """Получить URL базы данных из настроек"""
    try:
        settings = get_settings()
        return settings.database_url
    except Exception as e:
        print(f"❌ Ошибка получения URL БД: {e}")
        # Fallback на переменную окружения
        return os.getenv("DATABASE_URL", "sqlite:///./avito_ai.db")

def run_migrations_offline():
    """Запуск миграций в 'offline' режиме"""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,  # Важно для SQLite
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Запуск миграций в 'online' режиме"""
    # Устанавливаем URL в конфигурации
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    # Определяем параметры для разных типов БД
    url = get_url()
    connect_args = {}
    
    if "sqlite" in url.lower():
        # Настройки для SQLite
        connect_args = {
            "check_same_thread": False,
            "timeout": 30
        }
        poolclass = pool.StaticPool
    else:
        # Настройки для PostgreSQL
        poolclass = pool.NullPool
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=poolclass,
        connect_args=connect_args
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=True,  # Поддержка SQLite
        )

        with context.begin_transaction():
            context.run_migrations()

# Определяем режим запуска
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
