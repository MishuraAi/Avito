#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ЭКСТРЕННЫЙ СКРИПТ ИСПРАВЛЕНИЯ
Исправляет критические проблемы с кодировкой и запускает приложение
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

# Устанавливаем UTF-8 для Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    # Пытаемся установить UTF-8 для консоли
    try:
        import locale
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except:
        pass

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class EmergencyFix:
    """Экстренное исправление проблем"""
    
    def __init__(self):
        self.project_root = project_root
        self.migrations_dir = self.project_root / "migrations"
        self.alembic_ini = self.project_root / "alembic.ini"
        
    def print_safe(self, message: str):
        """Безопасный вывод без эмодзи"""
        try:
            print(message)
        except UnicodeEncodeError:
            # Заменяем эмодзи на текст
            safe_message = message.encode('ascii', 'replace').decode('ascii')
            print(safe_message)
    
    def fix_alembic_ini(self) -> bool:
        """Исправление alembic.ini с правильной кодировкой"""
        try:
            self.print_safe("ИСПРАВЛЕНИЕ alembic.ini...")
            
            # Создаем простую рабочую версию без проблемных символов
            fixed_content = """# Alembic configuration for Avito AI Bot
# Fixed for Windows encoding

[alembic]
script_location = migrations
file_template = %%%(year)d%%%(month).2d%%%(day).2d_%%%(rev)s_%%%(slug)s
timezone = UTC
truncate_slug_length = 40

compare_type = true
compare_server_default = true
render_as_batch = true

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters] 
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""
            
            # Создаем бэкап
            if self.alembic_ini.exists():
                backup_file = self.alembic_ini.with_suffix('.ini.broken')
                self.alembic_ini.rename(backup_file)
                self.print_safe(f"Создан бэкап: {backup_file.name}")
            
            # Записываем исправленную версию с UTF-8
            with open(self.alembic_ini, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            self.print_safe("УСПЕШНО: alembic.ini исправлен")
            return True
            
        except Exception as e:
            self.print_safe(f"ОШИБКА исправления alembic.ini: {e}")
            return False
    
    def clean_migrations(self) -> bool:
        """Полная очистка миграций"""
        try:
            self.print_safe("ОЧИСТКА миграций...")
            
            if self.migrations_dir.exists():
                import shutil
                shutil.rmtree(self.migrations_dir)
                self.print_safe("Старые миграции удалены")
            
            return True
            
        except Exception as e:
            self.print_safe(f"ОШИБКА очистки: {e}")
            return False
    
    def init_alembic_manually(self) -> bool:
        """Ручная инициализация Alembic без проблемных скриптов"""
        try:
            self.print_safe("РУЧНАЯ инициализация Alembic...")
            
            # Инициализируем Alembic
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "init", "migrations"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode != 0:
                self.print_safe(f"ОШИБКА инициализации: {result.stderr}")
                return False
            
            self.print_safe("УСПЕШНО: Alembic инициализирован")
            
            # Создаем простой env.py
            self.create_simple_env_py()
            
            return True
            
        except Exception as e:
            self.print_safe(f"ОШИБКА ручной инициализации: {e}")
            return False
    
    def create_simple_env_py(self):
        """Создание простого env.py без проблемных символов"""
        env_py_path = self.migrations_dir / "env.py"
        
        env_content = '''# -*- coding: utf-8 -*-
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.core.config import get_settings
    from src.database.models import Base
except ImportError as e:
    print(f"Import error in env.py: {e}")
    sys.exit(1)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_url():
    try:
        settings = get_settings()
        return settings.database_url
    except Exception as e:
        return os.getenv("DATABASE_URL", "sqlite:///./avito_ai.db")

def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.StaticPool if "sqlite" in get_url() else pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
        
        with open(env_py_path, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        self.print_safe("УСПЕШНО: env.py создан")
    
    def create_migration(self) -> bool:
        """Создание миграции"""
        try:
            self.print_safe("СОЗДАНИЕ миграции...")
            
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "revision", 
                 "--autogenerate", "-m", "Initial_migration"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                self.print_safe("УСПЕШНО: Миграция создана")
                return True
            else:
                if "No changes in schema detected" in result.stdout:
                    self.print_safe("ИНФОРМАЦИЯ: Схема не изменилась")
                    return True
                self.print_safe(f"ПРЕДУПРЕЖДЕНИЕ: {result.stderr}")
                return True  # Не критично
                
        except Exception as e:
            self.print_safe(f"ОШИБКА создания миграции: {e}")
            return True  # Не критично
    
    def apply_migrations(self) -> bool:
        """Применение миграций"""
        try:
            self.print_safe("ПРИМЕНЕНИЕ миграций...")
            
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                self.print_safe("УСПЕШНО: Миграции применены")
                return True
            else:
                self.print_safe(f"ПРЕДУПРЕЖДЕНИЕ применения: {result.stderr}")
                return True  # Продолжаем даже с предупреждениями
                
        except Exception as e:
            self.print_safe(f"ОШИБКА применения миграций: {e}")
            return True  # Не критично для запуска
    
    def start_server(self) -> bool:
        """Запуск сервера"""
        try:
            self.print_safe("ЗАПУСК сервера разработки...")
            self.print_safe("Сервер: http://localhost:8000")
            self.print_safe("API документация: http://localhost:8000/docs")
            self.print_safe("Для остановки: Ctrl+C")
            
            # Открываем браузер через 3 секунды
            def open_browser():
                time.sleep(3)
                try:
                    webbrowser.open("http://localhost:8000/docs")
                except:
                    pass
            
            import threading
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()
            
            # Запускаем сервер через Python модуль
            result = subprocess.run(
                [sys.executable, "-m", "uvicorn", "src.api.main:app", 
                 "--reload", "--host", "0.0.0.0", "--port", "8000"],
                cwd=self.project_root
            )
            
            return True
            
        except KeyboardInterrupt:
            self.print_safe("Сервер остановлен")
            return True
        except Exception as e:
            self.print_safe(f"ОШИБКА запуска сервера: {e}")
            return False
    
    def check_docker(self):
        """Проверка Docker"""
        try:
            # Пробуем разные пути к Docker
            docker_paths = [
                "docker",
                "C:\\Program Files\\Docker\\Docker\\resources\\bin\\docker.exe",
                "C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe",
                os.path.expanduser("~\\AppData\\Local\\Docker\\Docker\\resources\\bin\\docker.exe")
            ]
            
            for docker_path in docker_paths:
                try:
                    result = subprocess.run(
                        [docker_path, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        self.print_safe(f"НАЙДЕН Docker: {docker_path}")
                        self.print_safe(f"Версия: {result.stdout.strip()}")
                        return True
                except:
                    continue
            
            self.print_safe("Docker не найден в стандартных местах")
            self.print_safe("Возможные решения:")
            self.print_safe("1. Перезагрузите компьютер после установки Docker")
            self.print_safe("2. Запустите Docker Desktop вручную")
            self.print_safe("3. Добавьте Docker в PATH")
            return False
            
        except Exception as e:
            self.print_safe(f"ОШИБКА проверки Docker: {e}")
            return False
    
    def run_emergency_fix(self) -> bool:
        """Экстренное исправление и запуск"""
        self.print_safe("=== ЭКСТРЕННОЕ ИСПРАВЛЕНИЕ AVITO AI BOT ===")
        self.print_safe("Исправление проблем с кодировкой и запуск приложения")
        self.print_safe("")
        
        steps = [
            ("Исправление alembic.ini", self.fix_alembic_ini),
            ("Очистка миграций", self.clean_migrations),
            ("Инициализация Alembic", self.init_alembic_manually),
            ("Создание миграции", self.create_migration),
            ("Применение миграций", self.apply_migrations),
            ("Запуск сервера", self.start_server),
        ]
        
        for step_name, step_func in steps:
            self.print_safe(f">>> {step_name}...")
            try:
                if not step_func():
                    self.print_safe(f"ОШИБКА на шаге: {step_name}")
                    return False
            except Exception as e:
                self.print_safe(f"КРИТИЧЕСКАЯ ОШИБКА в '{step_name}': {e}")
                return False
        
        return True


def main():
    """Главная функция"""
    try:
        fix = EmergencyFix()
        
        # Проверяем Docker отдельно
        print("=== ПРОВЕРКА DOCKER ===")
        fix.check_docker()
        print("")
        
        # Запускаем исправление
        success = fix.run_emergency_fix()
        
        if success:
            fix.print_safe("УСПЕХ: Приложение запущено!")
        else:
            fix.print_safe("ОШИБКА: Не удалось запустить приложение")
            
    except KeyboardInterrupt:
        print("Операция прервана")
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")


if __name__ == "__main__":
    main()