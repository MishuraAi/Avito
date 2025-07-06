#!/usr/bin/env python3
"""
🔄 Скрипт инициализации миграций Alembic для проекта Avito AI Bot

КОМПЛЕКСНОЕ РЕШЕНИЕ с учетом всестороннего анализа:
1. ✅ Кроссплатформенная совместимость (Windows/Linux/macOS)
2. ✅ Поддержка SQLite и PostgreSQL 
3. ✅ Унифицированный подход к вызову Alembic
4. ✅ Детальная диагностика и обработка ошибок
5. ✅ Совместимость с существующей архитектурой проекта

Местоположение: scripts/init_migrations.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
import platform

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.core.config import get_settings
    from src.database.models import Base
    from sqlalchemy import create_engine, text, inspect
    from sqlalchemy.exc import OperationalError
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("📝 Убедитесь что установлены все зависимости:")
    print("   pip install -r requirements-dev.txt")
    sys.exit(1)


class CrossPlatformMigrationInitializer:
    """
    🌍 Кроссплатформенный инициализатор миграций
    
    Поддерживает:
    - Windows/Linux/macOS
    - SQLite/PostgreSQL
    - Различные методы установки Python/Alembic
    """
    
    def __init__(self):
        self.project_root = project_root
        self.migrations_dir = self.project_root / "migrations"
        self.alembic_ini = self.project_root / "alembic.ini"
        self.platform = platform.system()
        self.settings = None
        self.db_type = None
        
        # Статистика выполнения
        self.execution_stats = {
            "platform": self.platform,
            "python_version": platform.python_version(),
            "steps_completed": 0,
            "total_steps": 8,
            "warnings": [],
            "errors": []
        }
        
    def log_step(self, step_name: str, success: bool = True, warning: str = None):
        """Логирование шагов выполнения"""
        if success:
            self.execution_stats["steps_completed"] += 1
            print(f"✅ {step_name}")
        else:
            self.execution_stats["errors"].append(step_name)
            print(f"❌ {step_name}")
            
        if warning:
            self.execution_stats["warnings"].append(warning)
            print(f"⚠️ {warning}")
    
    def check_alembic_availability(self) -> Dict[str, Any]:
        """
        Комплексная проверка доступности Alembic
        
        Returns:
            Dict[str, Any]: Результаты проверки
        """
        print("🔍 Проверка доступности Alembic...")
        
        result = {
            "direct_command": False,
            "python_module": False,
            "version": None,
            "recommended_method": None,
            "installation_path": None
        }
        
        # 1. Проверяем прямую команду alembic
        try:
            proc = subprocess.run(
                ["alembic", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if proc.returncode == 0:
                result["direct_command"] = True
                result["version"] = proc.stdout.strip()
                result["recommended_method"] = "alembic"
                print("✅ Команда 'alembic' доступна напрямую")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            print("⚠️ Команда 'alembic' не найдена в PATH")
        
        # 2. Проверяем через python -m alembic
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "alembic", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if proc.returncode == 0:
                result["python_module"] = True
                if not result["version"]:
                    result["version"] = proc.stdout.strip()
                if not result["recommended_method"]:
                    result["recommended_method"] = "python -m alembic"
                print("✅ Alembic доступен через 'python -m alembic'")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            print("❌ Alembic недоступен через 'python -m alembic'")
        
        # 3. Определяем оптимальный метод
        if not result["direct_command"] and not result["python_module"]:
            print("❌ Alembic не установлен или недоступен!")
            print("📦 Установите: pip install alembic")
            return result
        
        # Предпочитаем python -m alembic для кроссплатформенности
        if result["python_module"]:
            result["recommended_method"] = "python -m alembic"
            print(f"🎯 Рекомендуемый метод: {result['recommended_method']}")
        
        return result
    
    def get_alembic_command(self) -> list:
        """
        Получить команду для запуска Alembic
        
        Returns:
            list: Команда для subprocess
        """
        alembic_check = self.check_alembic_availability()
        
        if not alembic_check["python_module"] and not alembic_check["direct_command"]:
            raise RuntimeError("Alembic недоступен")
        
        # Всегда предпочитаем python -m alembic для стабильности
        if alembic_check["python_module"]:
            return [sys.executable, "-m", "alembic"]
        else:
            return ["alembic"]
    
    def load_and_analyze_settings(self) -> bool:
        """
        Загрузка и анализ настроек проекта
        
        Returns:
            bool: True если успешно
        """
        try:
            print("⚙️ Загрузка настроек проекта...")
            
            self.settings = get_settings()
            
            # Определяем тип базы данных
            db_url = self.settings.database_url.lower()
            if "sqlite" in db_url:
                self.db_type = "sqlite"
                print(f"🗄️ Обнаружена SQLite база: {self.settings.database_url}")
            elif "postgresql" in db_url:
                self.db_type = "postgresql"
                print(f"🐘 Обнаружена PostgreSQL база: {self._mask_password(self.settings.database_url)}")
            else:
                self.db_type = "unknown"
                print(f"❓ Неизвестный тип БД: {self._mask_password(self.settings.database_url)}")
            
            self.log_step("Настройки загружены", True)
            return True
            
        except Exception as e:
            self.log_step("Ошибка загрузки настроек", False)
            print(f"   Детали: {e}")
            print("📝 Проверьте файл .env и зависимости")
            return False
    
    def _mask_password(self, url: str) -> str:
        """Скрыть пароль в URL для безопасного вывода"""
        if "://" in url and "@" in url:
            parts = url.split("://")
            if len(parts) == 2:
                protocol = parts[0]
                rest = parts[1]
                if "@" in rest:
                    auth_part, host_part = rest.split("@", 1)
                    if ":" in auth_part:
                        user, _ = auth_part.split(":", 1)
                        return f"{protocol}://{user}:***@{host_part}"
        return url
    
    def test_database_connection(self) -> bool:
        """
        Тестирование подключения к базе данных
        
        Returns:
            bool: True если подключение успешно
        """
        try:
            print("🔌 Тестирование подключения к базе данных...")
            
            engine = create_engine(self.settings.database_url)
            
            with engine.connect() as conn:
                if self.db_type == "sqlite":
                    result = conn.execute(text("SELECT sqlite_version()"))
                    version = result.fetchone()[0]
                    print(f"✅ SQLite версия: {version}")
                    
                    # Для SQLite проверяем, что файл БД доступен для записи
                    if ":///" in self.settings.database_url:
                        db_path = self.settings.database_url.split("///")[1]
                        if db_path != ":memory:":
                            db_file = Path(db_path)
                            db_dir = db_file.parent
                            if not db_dir.exists():
                                db_dir.mkdir(parents=True, exist_ok=True)
                                print(f"📁 Создана директория для БД: {db_dir}")
                            
                elif self.db_type == "postgresql":
                    result = conn.execute(text("SELECT version()"))
                    version = result.fetchone()[0]
                    print(f"✅ PostgreSQL: {version[:50]}...")
                else:
                    # Универсальная проверка
                    conn.execute(text("SELECT 1"))
                    print(f"✅ Подключение к БД успешно")
            
            self.log_step("Подключение к БД протестировано", True)
            return True
            
        except OperationalError as e:
            self.log_step("Ошибка подключения к БД", False)
            print(f"   Детали: {e}")
            
            if self.db_type == "sqlite":
                print("\n📋 Возможные решения для SQLite:")
                print("   1. Проверьте права на запись в директорию")
                print("   2. Убедитесь что диск не переполнен")
                print("   3. Проверьте путь к файлу БД в .env")
            elif self.db_type == "postgresql":
                print("\n📋 Возможные решения для PostgreSQL:")
                print("   1. Запустите PostgreSQL сервер")
                print("   2. Проверьте настройки подключения в .env")
                print("   3. Создайте базу данных: python scripts/setup_database.py")
            
            return False
        except Exception as e:
            self.log_step("Неожиданная ошибка БД", False)
            print(f"   Детали: {e}")
            return False
    
    def clean_existing_migrations(self) -> bool:
        """
        Очистка существующих неполных миграций
        
        Returns:
            bool: True если очистка выполнена или не требуется
        """
        try:
            print("🧹 Проверка существующих миграций...")
            
            if not self.migrations_dir.exists():
                print("ℹ️ Папка migrations не существует")
                self.log_step("Очистка миграций не требуется", True)
                return True
            
            # Проверяем целостность структуры миграций
            required_files = ["env.py", "script.py.mako"]
            missing_files = []
            
            for file_name in required_files:
                if not (self.migrations_dir / file_name).exists():
                    missing_files.append(file_name)
            
            if missing_files:
                print(f"⚠️ Обнаружена неполная структура миграций")
                print(f"   Отсутствуют: {', '.join(missing_files)}")
                
                response = input("❓ Удалить неполную структуру и пересоздать? (y/n): ").lower().strip()
                if response == 'y':
                    shutil.rmtree(self.migrations_dir)
                    print("🗑️ Неполная структура миграций удалена")
                    self.log_step("Неполные миграции очищены", True)
                    return True
                else:
                    print("⚠️ Оставляем существующую структуру")
                    self.log_step("Очистка миграций пропущена", True, "Может возникнуть конфликт")
                    return True
            else:
                print("✅ Структура миграций корректна")
                
                # Проверяем наличие файлов версий
                versions_dir = self.migrations_dir / "versions"
                if versions_dir.exists() and any(versions_dir.iterdir()):
                    version_files = list(versions_dir.glob("*.py"))
                    print(f"📋 Найдено {len(version_files)} файлов миграций")
                    
                    response = input("❓ Создать новую миграцию к существующим? (y/n): ").lower().strip()
                    if response != 'y':
                        print("ℹ️ Пропускаем создание миграции")
                        return False
                
                self.log_step("Существующие миграции проверены", True)
                return True
                
        except Exception as e:
            self.log_step("Ошибка очистки миграций", False)
            print(f"   Детали: {e}")
            return False
    
    def initialize_alembic(self) -> bool:
        """
        Инициализация Alembic с кроссплатформенной поддержкой
        
        Returns:
            bool: True если инициализация успешна
        """
        try:
            print("🔄 Инициализация Alembic...")
            
            if self.migrations_dir.exists() and (self.migrations_dir / "env.py").exists():
                print("ℹ️ Alembic уже инициализирован")
                self.log_step("Alembic уже инициализирован", True)
                return True
            
            # Получаем команду для запуска Alembic
            alembic_cmd = self.get_alembic_command()
            
            # Выполняем инициализацию
            init_cmd = alembic_cmd + ["init", "migrations"]
            
            print(f"🚀 Выполняем: {' '.join(init_cmd)}")
            
            result = subprocess.run(
                init_cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                self.log_step("Ошибка инициализации Alembic", False)
                print(f"   Код ошибки: {result.returncode}")
                print(f"   Ошибка: {result.stderr}")
                print(f"   Вывод: {result.stdout}")
                return False
            
            print("✅ Alembic успешно инициализирован")
            self.log_step("Alembic инициализирован", True)
            return True
            
        except subprocess.TimeoutExpired:
            self.log_step("Таймаут инициализации Alembic", False)
            print("   Команда выполняется слишком долго")
            return False
        except Exception as e:
            self.log_step("Неожиданная ошибка инициализации", False)
            print(f"   Детали: {e}")
            return False
    
    def configure_alembic_ini(self) -> bool:
        """
        Настройка alembic.ini с учетом типа БД
        
        Returns:
            bool: True если настройка успешна
        """
        try:
            print("⚙️ Настройка alembic.ini...")
            
            if not self.alembic_ini.exists():
                self.log_step("alembic.ini не найден", False)
                return False
            
            # Читаем существующий файл
            content = self.alembic_ini.read_text(encoding='utf-8')
            
            # Определяем настройки в зависимости от типа БД
            if self.db_type == "sqlite":
                # Для SQLite добавляем поддержку WAL режима
                additional_config = """
# SQLite specific settings
sqlalchemy.url = 
sqlalchemy.echo = false
sqlalchemy.echo_pool = false
sqlalchemy.pool_pre_ping = true

# SQLite performance settings
[sqlalchemy]
url = 
echo = false
poolclass = StaticPool
pool_pre_ping = true
connect_args = {"check_same_thread": false, "timeout": 30}
"""
            else:
                # Для PostgreSQL стандартные настройки
                additional_config = """
# PostgreSQL specific settings
sqlalchemy.url = 
sqlalchemy.echo = false
sqlalchemy.pool_size = 5
sqlalchemy.max_overflow = 10
sqlalchemy.pool_timeout = 30
sqlalchemy.pool_recycle = 3600
"""
            
            # Добавляем настройки если их нет
            if "sqlalchemy.pool_pre_ping" not in content:
                content = content.replace(
                    "sqlalchemy.url = ",
                    "sqlalchemy.url = " + additional_config
                )
                
                # Записываем обновленный файл
                self.alembic_ini.write_text(content, encoding='utf-8')
                print(f"✅ alembic.ini настроен для {self.db_type}")
            else:
                print("ℹ️ alembic.ini уже настроен")
            
            self.log_step("alembic.ini настроен", True)
            return True
            
        except Exception as e:
            self.log_step("Ошибка настройки alembic.ini", False)
            print(f"   Детали: {e}")
            return False
    
    def configure_env_py(self) -> bool:
        """
        Настройка migrations/env.py для проекта
        
        Returns:
            bool: True если настройка успешна
        """
        try:
            print("⚙️ Настройка migrations/env.py...")
            
            env_py_path = self.migrations_dir / "env.py"
            
            if not env_py_path.exists():
                self.log_step("env.py не найден", False)
                return False
            
            # Создаем улучшенный env.py с поддержкой нашей архитектуры
            env_content = '''"""
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
'''
            
            # Записываем новый env.py
            env_py_path.write_text(env_content, encoding='utf-8')
            
            print("✅ migrations/env.py настроен для проекта")
            self.log_step("env.py настроен", True)
            return True
            
        except Exception as e:
            self.log_step("Ошибка настройки env.py", False)
            print(f"   Детали: {e}")
            return False
    
    def create_initial_migration(self) -> bool:
        """
        Создание первой миграции с автогенерацией
        
        Returns:
            bool: True если миграция создана
        """
        try:
            print("📝 Создание первой миграции...")
            
            # Проверяем, есть ли уже миграции
            versions_dir = self.migrations_dir / "versions"
            if versions_dir.exists() and any(versions_dir.glob("*.py")):
                existing_migrations = list(versions_dir.glob("*.py"))
                print(f"ℹ️ Найдено {len(existing_migrations)} существующих миграций")
                
                response = input("❓ Создать новую миграцию? (y/n): ").lower().strip()
                if response != 'y':
                    print("ℹ️ Создание миграции пропущено")
                    self.log_step("Создание миграции пропущено", True)
                    return True
            
            # Получаем команду для запуска Alembic
            alembic_cmd = self.get_alembic_command()
            
            # Создаем миграцию
            revision_cmd = alembic_cmd + [
                "revision", 
                "--autogenerate", 
                "-m", 
                "Initial migration - create all tables"
            ]
            
            print(f"🚀 Выполняем: {' '.join(revision_cmd)}")
            
            result = subprocess.run(
                revision_cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                self.log_step("Ошибка создания миграции", False)
                print(f"   Код ошибки: {result.returncode}")
                print(f"   Ошибка: {result.stderr}")
                print(f"   Вывод: {result.stdout}")
                
                # Дополнительная диагностика
                if "No changes in schema detected" in result.stdout:
                    print("ℹ️ В схеме БД нет изменений - это нормально")
                    self.log_step("Миграция не требуется", True, "Схема БД не изменилась")
                    return True
                
                return False
            
            print("✅ Первая миграция создана успешно")
            if result.stdout:
                print(f"📋 Детали: {result.stdout.strip()}")
            
            # Показываем созданные файлы
            versions_dir = self.migrations_dir / "versions"
            if versions_dir.exists():
                migration_files = list(versions_dir.glob("*.py"))
                print(f"📁 Создано файлов миграций: {len(migration_files)}")
                for mf in migration_files[-3:]:  # Показываем последние 3
                    print(f"   - {mf.name}")
            
            self.log_step("Первая миграция создана", True)
            return True
            
        except subprocess.TimeoutExpired:
            self.log_step("Таймаут создания миграции", False)
            print("   Создание миграции выполняется слишком долго")
            return False
        except Exception as e:
            self.log_step("Неожиданная ошибка создания миграции", False)
            print(f"   Детали: {e}")
            return False
    
    def verify_migration_status(self) -> bool:
        """
        Проверка статуса миграций
        
        Returns:
            bool: True если проверка прошла успешно
        """
        try:
            print("🔍 Проверка статуса миграций...")
            
            alembic_cmd = self.get_alembic_command()
            
            # Проверяем текущую версию
            current_cmd = alembic_cmd + ["current"]
            
            result = subprocess.run(
                current_cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                if result.stdout.strip():
                    print(f"📍 Текущая версия миграций: {result.stdout.strip()}")
                else:
                    print("📍 Миграции еще не применены к БД")
            
            # Показываем историю миграций
            history_cmd = alembic_cmd + ["history"]
            
            result = subprocess.run(
                history_cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                print("📚 История миграций:")
                # Показываем только последние строки для краткости
                lines = result.stdout.strip().split('\n')
                for line in lines[-5:]:
                    if line.strip():
                        print(f"   {line}")
            
            self.log_step("Статус миграций проверен", True)
            return True
            
        except Exception as e:
            self.log_step("Ошибка проверки статуса", False)
            print(f"   Детали: {e}")
            # Не критическая ошибка
            return True
    
    def run_comprehensive_initialization(self) -> bool:
        """
        Запуск полной инициализации с комплексным анализом
        
        Returns:
            bool: True если инициализация успешна
        """
        print("🚀 Комплексная инициализация миграций для Avito AI Bot")
        print("=" * 60)
        print(f"🌍 Платформа: {self.platform}")
        print(f"🐍 Python: {platform.python_version()}")
        print(f"📁 Проект: {self.project_root}")
        print("=" * 60)
        
        # Шаги инициализации
        steps = [
            ("Загрузка настроек проекта", self.load_and_analyze_settings),
            ("Тестирование подключения к БД", self.test_database_connection),
            ("Очистка существующих миграций", self.clean_existing_migrations),
            ("Инициализация Alembic", self.initialize_alembic),
            ("Настройка alembic.ini", self.configure_alembic_ini),
            ("Настройка env.py", self.configure_env_py),
            ("Создание первой миграции", self.create_initial_migration),
            ("Проверка статуса миграций", self.verify_migration_status),
        ]
        
        # Выполняем шаги последовательно
        for step_name, step_func in steps:
            print(f"\n🔄 {step_name}...")
            try:
                if not step_func():
                    print(f"\n❌ Инициализация остановлена на шаге: {step_name}")
                    self._print_execution_summary(False)
                    return False
            except Exception as e:
                print(f"❌ Критическая ошибка в шаге '{step_name}': {e}")
                self._print_execution_summary(False)
                return False
        
        # Успешное завершение
        self._print_execution_summary(True)
        return True
    
    def _print_execution_summary(self, success: bool):
        """Вывод итогового отчета"""
        print("\n" + "=" * 60)
        
        if success:
            print("🎉 ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        else:
            print("❌ ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА С ОШИБКАМИ")
        
        print(f"📊 Статистика выполнения:")
        print(f"   ✅ Шагов завершено: {self.execution_stats['steps_completed']}/{self.execution_stats['total_steps']}")
        print(f"   🌍 Платформа: {self.execution_stats['platform']}")
        print(f"   🐍 Python: {self.execution_stats['python_version']}")
        print(f"   🗄️ Тип БД: {self.db_type or 'не определен'}")
        
        if self.execution_stats['warnings']:
            print(f"   ⚠️ Предупреждений: {len(self.execution_stats['warnings'])}")
            for warning in self.execution_stats['warnings']:
                print(f"      - {warning}")
        
        if self.execution_stats['errors']:
            print(f"   ❌ Ошибок: {len(self.execution_stats['errors'])}")
            for error in self.execution_stats['errors']:
                print(f"      - {error}")
        
        if success:
            print(f"\n📋 Следующие шаги:")
            
            # Показываем подходящие команды для платформы
            alembic_cmd = "python -m alembic" if self.platform == "Windows" else "alembic"
            
            print(f"1. Просмотр миграций: {alembic_cmd} history")
            print(f"2. Применение миграций: {alembic_cmd} upgrade head")
            print(f"3. Проверка статуса: {alembic_cmd} current")
            print(f"4. Запуск приложения: uvicorn src.api.main:app --reload")
            
            print(f"\n📁 Созданные файлы:")
            print(f"   - {self.migrations_dir}/env.py")
            print(f"   - {self.migrations_dir}/script.py.mako")
            print(f"   - {self.migrations_dir}/versions/*.py")
            print(f"   - {self.alembic_ini}")


def main():
    """Главная функция"""
    try:
        initializer = CrossPlatformMigrationInitializer()
        success = initializer.run_comprehensive_initialization()
        
        if success:
            print("\n✅ Скрипт выполнен успешно")
            sys.exit(0)
        else:
            print("\n❌ Скрипт завершился с ошибками")
            print("📝 Проверьте логи выше для диагностики проблем")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Выполнение прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()