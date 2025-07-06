#!/usr/bin/env python3
"""
🚀 Скрипт запуска локальной разработки Avito AI Bot

Этот скрипт:
1. Проверяет и исправляет миграции
2. Инициализирует базу данных
3. Запускает приложение в режиме разработки
4. Открывает браузер с API документацией

Использование для локальной разработки без Docker
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class LocalDevSetup:
    """Класс для настройки локальной разработки"""
    
    def __init__(self):
        self.project_root = project_root
        self.migrations_dir = self.project_root / "migrations"
        self.alembic_ini = self.project_root / "alembic.ini"
        
    def check_environment(self) -> bool:
        """Проверка окружения разработки"""
        try:
            print("🔍 Проверка окружения разработки...")
            
            # Проверяем Python
            python_version = sys.version
            print(f"✅ Python: {python_version.split()[0]}")
            
            # Проверяем зависимости
            try:
                import fastapi
                import uvicorn
                import sqlalchemy
                import alembic
                print("✅ Основные зависимости установлены")
            except ImportError as e:
                print(f"❌ Отсутствует зависимость: {e}")
                print("📦 Установите: pip install -r requirements-dev.txt")
                return False
            
            # Проверяем .env файл
            env_file = self.project_root / ".env"
            if not env_file.exists():
                print("⚠️ Файл .env не найден, создаем базовый...")
                self.create_basic_env()
            else:
                print("✅ Файл .env найден")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка проверки окружения: {e}")
            return False
    
    def create_basic_env(self) -> bool:
        """Создание базового .env файла для разработки"""
        try:
            env_content = """# 🔧 Локальные настройки разработки для Avito AI Bot

# Основные настройки
DEBUG=true
ENVIRONMENT=development
SECRET_KEY=local-dev-secret-key-not-for-production
JWT_SECRET_KEY=local-dev-jwt-secret-not-for-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# База данных SQLite (для локальной разработки)
DATABASE_URL=sqlite:///./avito_ai.db
TEST_DATABASE_URL=sqlite:///./avito_ai_test.db

# Redis (пока не используется локально)
REDIS_URL=redis://localhost:6379/0

# API ключи (ЗАМЕНИТЕ НА РЕАЛЬНЫЕ!)
GEMINI_API_KEY=your-real-gemini-api-key-here
AVITO_CLIENT_ID=your-real-avito-client-id-here
AVITO_CLIENT_SECRET=your-real-avito-client-secret-here

# CORS для локальной разработки
CORS_ORIGINS=http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000

# Логирование
LOG_LEVEL=DEBUG
LOG_FILE_PATH=data/logs/app.log

# Сервер
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
"""
            
            env_file = self.project_root / ".env"
            env_file.write_text(env_content, encoding='utf-8')
            
            print("✅ Базовый .env файл создан")
            print("⚠️ Не забудьте заменить API ключи на реальные!")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания .env: {e}")
            return False
    
    def fix_alembic_config(self) -> bool:
        """Исправление конфигурации Alembic"""
        try:
            print("🔧 Исправление конфигурации Alembic...")
            
            if not self.alembic_ini.exists():
                print("⚠️ alembic.ini не найден")
                return False
            
            # Читаем содержимое
            content = self.alembic_ini.read_text(encoding='utf-8')
            
            # Проверяем на дублирующиеся настройки
            if content.count('sqlalchemy.url') > 1:
                print("🔍 Обнаружены дублирующиеся настройки, исправляем...")
                
                # Создаем исправленную версию
                fixed_content = """# Конфигурация Alembic для Avito AI Responder
# Исправлено для локальной разработки

[alembic]
script_location = migrations
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s
timezone = UTC
truncate_slug_length = 40

# URL базы данных берется из env.py
# sqlalchemy.url = 

sqlalchemy.echo = false
sqlalchemy.pool_pre_ping = true
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
                backup_file = self.alembic_ini.with_suffix('.ini.backup')
                backup_file.write_text(content, encoding='utf-8')
                
                # Записываем исправленную версию
                self.alembic_ini.write_text(fixed_content, encoding='utf-8')
                print("✅ alembic.ini исправлен (создан бэкап)")
            else:
                print("✅ alembic.ini в порядке")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка исправления alembic.ini: {e}")
            return False
    
    def clean_migrations(self) -> bool:
        """Очистка проблемных миграций"""
        try:
            print("🧹 Очистка миграций...")
            
            if self.migrations_dir.exists():
                # Проверяем целостность
                required_files = ["env.py", "script.py.mako"]
                missing_files = [f for f in required_files 
                               if not (self.migrations_dir / f).exists()]
                
                if missing_files:
                    print(f"⚠️ Неполная структура миграций (отсутствуют: {missing_files})")
                    response = input("❓ Удалить и пересоздать? (y/n): ").lower().strip()
                    if response == 'y':
                        import shutil
                        shutil.rmtree(self.migrations_dir)
                        print("🗑️ Старые миграции удалены")
                    else:
                        print("⚠️ Оставляем как есть")
                else:
                    print("✅ Структура миграций корректна")
            else:
                print("ℹ️ Папка migrations не существует")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка очистки миграций: {e}")
            return False
    
    def init_migrations(self) -> bool:
        """Инициализация миграций"""
        try:
            print("🔄 Инициализация миграций...")
            
            # Запускаем скрипт инициализации миграций
            result = subprocess.run(
                [sys.executable, "scripts/init_migrations.py"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Миграции инициализированы успешно")
                return True
            else:
                print("❌ Ошибка инициализации миграций:")
                print(result.stderr)
                
                # Пробуем ручную инициализацию
                print("🔄 Попытка ручной инициализации...")
                return self.manual_migration_init()
                
        except Exception as e:
            print(f"❌ Ошибка инициализации: {e}")
            return self.manual_migration_init()
    
    def manual_migration_init(self) -> bool:
        """Ручная инициализация миграций"""
        try:
            print("🔧 Ручная инициализация миграций...")
            
            # Инициализируем Alembic
            if not self.migrations_dir.exists():
                result = subprocess.run(
                    [sys.executable, "-m", "alembic", "init", "migrations"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    print(f"❌ Ошибка: {result.stderr}")
                    return False
                
                print("✅ Структура миграций создана")
            
            # Создаем первую миграцию
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "revision", "--autogenerate", 
                 "-m", "Initial migration"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"⚠️ Возможная ошибка при создании миграции: {result.stderr}")
                if "No changes in schema detected" in result.stdout:
                    print("ℹ️ Изменения в схеме не обнаружены - это нормально")
                    return True
                return False
            
            print("✅ Первая миграция создана")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка ручной инициализации: {e}")
            return False
    
    def apply_migrations(self) -> bool:
        """Применение миграций"""
        try:
            print("📝 Применение миграций к базе данных...")
            
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Миграции применены успешно")
                return True
            else:
                print("❌ Ошибка применения миграций:")
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ Ошибка применения миграций: {e}")
            return False
    
    def test_database(self) -> bool:
        """Тестирование базы данных"""
        try:
            print("🧪 Тестирование базы данных...")
            
            result = subprocess.run(
                [sys.executable, "scripts/check_database.py"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ База данных работает корректно")
                return True
            else:
                print("⚠️ Предупреждения при проверке БД:")
                print(result.stdout)
                return True  # Не критично для разработки
                
        except Exception as e:
            print(f"⚠️ Ошибка тестирования БД: {e}")
            return True  # Не критично
    
    def start_development_server(self) -> bool:
        """Запуск сервера разработки"""
        try:
            print("🚀 Запуск сервера разработки...")
            print("📁 Рабочая директория:", self.project_root)
            print("🌐 Сервер будет доступен на: http://localhost:8000")
            print("📚 API документация: http://localhost:8000/docs")
            print("\n⏹️ Для остановки нажмите Ctrl+C")
            
            # Открываем браузер через 3 секунды
            def open_browser():
                time.sleep(3)
                try:
                    webbrowser.open("http://localhost:8000/docs")
                    print("🌐 Браузер открыт с API документацией")
                except:
                    pass
            
            import threading
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()
            
            # Запускаем сервер
            result = subprocess.run(
                [sys.executable, "-m", "uvicorn", "src.api.main:app", 
                 "--reload", "--host", "0.0.0.0", "--port", "8000"],
                cwd=self.project_root
            )
            
            return True
            
        except KeyboardInterrupt:
            print("\n⏹️ Сервер остановлен пользователем")
            return True
        except Exception as e:
            print(f"❌ Ошибка запуска сервера: {e}")
            return False
    
    def run_full_setup(self) -> bool:
        """Полная настройка локальной разработки"""
        print("🚀 Настройка локальной разработки Avito AI Bot")
        print("=" * 60)
        
        steps = [
            ("Проверка окружения", self.check_environment),
            ("Исправление Alembic", self.fix_alembic_config),
            ("Очистка миграций", self.clean_migrations),
            ("Инициализация миграций", self.init_migrations),
            ("Применение миграций", self.apply_migrations),
            ("Тестирование БД", self.test_database),
        ]
        
        for step_name, step_func in steps:
            print(f"\n🔄 {step_name}...")
            try:
                if not step_func():
                    print(f"\n❌ Ошибка на шаге: {step_name}")
                    return False
            except Exception as e:
                print(f"❌ Критическая ошибка в '{step_name}': {e}")
                return False
        
        print("\n" + "=" * 60)
        print("🎉 НАСТРОЙКА ЗАВЕРШЕНА УСПЕШНО!")
        print("\n📋 Что готово:")
        print("   ✅ База данных SQLite")
        print("   ✅ Миграции применены")
        print("   ✅ Конфигурация исправлена")
        print("   ✅ Сервер готов к запуску")
        
        print(f"\n🚀 Запускаем сервер разработки...")
        return self.start_development_server()


def main():
    """Главная функция"""
    try:
        setup = LocalDevSetup()
        success = setup.run_full_setup()
        
        if success:
            print("\n✅ Локальная разработка готова!")
            sys.exit(0)
        else:
            print("\n❌ Ошибка настройки локальной разработки")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Настройка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()