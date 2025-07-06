#!/usr/bin/env python3
"""
🧪 Полное тестирование настройки проекта Avito AI Bot

Этот скрипт проводит комплексное тестирование:
1. Проверка базы данных
2. Тестирование миграций
3. Проверка FastAPI приложения
4. Тестирование всех компонентов системы
"""

import os
import sys
import subprocess
import asyncio
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from sqlalchemy import create_engine, text
    from alembic.config import Config
    from alembic import command
    from alembic.script import ScriptDirectory
    from alembic.runtime.environment import EnvironmentContext
    import requests
    import psutil
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("📝 Установите зависимости: pip install -r requirements-dev.txt")
    sys.exit(1)


class CompleteSetupTester:
    """Класс для полного тестирования настройки проекта"""
    
    def __init__(self):
        self.project_root = project_root
        self.results: Dict[str, bool] = {}
        self.errors: List[str] = []
        
    def log_result(self, test_name: str, success: bool, error_msg: str = ""):
        """Записать результат теста"""
        self.results[test_name] = success
        if not success and error_msg:
            self.errors.append(f"{test_name}: {error_msg}")
    
    def run_command(self, command: List[str], cwd: Path = None) -> Tuple[bool, str, str]:
        """Выполнить системную команду"""
        try:
            result = subprocess.run(
                command,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Превышено время ожидания"
        except Exception as e:
            return False, "", str(e)
    
    def test_environment_setup(self) -> bool:
        """Тест 1: Проверка окружения"""
        print("🔄 Тест 1: Проверка окружения...")
        
        try:
            # Проверяем Python версию
            python_version = sys.version_info
            if python_version < (3, 11):
                self.log_result("Python версия", False, f"Требуется Python 3.11+, найдено {python_version}")
                return False
            
            print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
            
            # Проверяем .env файл
            env_path = self.project_root / ".env"
            if not env_path.exists():
                self.log_result(".env файл", False, "Файл .env не найден")
                return False
            
            print("✅ Файл .env найден")
            
            # Проверяем зависимости
            try:
                import fastapi
                import sqlalchemy
                import alembic
                print("✅ Основные зависимости установлены")
            except ImportError as e:
                self.log_result("Зависимости", False, f"Отсутствует зависимость: {e}")
                return False
            
            self.log_result("Окружение", True)
            return True
            
        except Exception as e:
            self.log_result("Окружение", False, str(e))
            return False
    
    def test_database_connection(self) -> bool:
        """Тест 2: Подключение к базе данных"""
        print("🔄 Тест 2: Подключение к базе данных...")
        
        success, stdout, stderr = self.run_command([
            sys.executable, "scripts/check_database.py"
        ])
        
        if success:
            print("✅ База данных подключена и настроена")
            self.log_result("Подключение к БД", True)
            return True
        else:
            print(f"❌ Ошибка подключения к БД: {stderr}")
            self.log_result("Подключение к БД", False, stderr)
            return False
    
    def test_migrations_initialization(self) -> bool:
        """Тест 3: Инициализация миграций"""
        print("🔄 Тест 3: Инициализация миграций...")
        
        try:
            # Проверяем существование папки migrations
            migrations_dir = self.project_root / "migrations"
            if not migrations_dir.exists():
                print("📁 Папка migrations не найдена, запускаем инициализацию...")
                
                success, stdout, stderr = self.run_command([
                    sys.executable, "scripts/init_migrations.py"
                ])
                
                if not success:
                    self.log_result("Инициализация миграций", False, stderr)
                    return False
            
            # Проверяем структуру миграций
            required_files = ["env.py", "script.py.mako", "versions"]
            for req_file in required_files:
                file_path = migrations_dir / req_file
                if not file_path.exists():
                    self.log_result("Структура миграций", False, f"Отсутствует {req_file}")
                    return False
            
            print("✅ Миграции инициализированы")
            self.log_result("Инициализация миграций", True)
            return True
            
        except Exception as e:
            self.log_result("Инициализация миграций", False, str(e))
            return False
    
    def test_migration_creation(self) -> bool:
        """Тест 4: Создание миграции"""
        print("🔄 Тест 4: Создание миграции...")
        
        try:
            # Проверяем конфигурацию Alembic
            alembic_cfg = Config(str(self.project_root / "alembic.ini"))
            
            # Проверяем версии миграций
            script_dir = ScriptDirectory.from_config(alembic_cfg)
            revisions = list(script_dir.walk_revisions())
            
            if not revisions:
                print("📝 Миграции не найдены, создаем первую миграцию...")
                
                success, stdout, stderr = self.run_command([
                    "alembic", "revision", "--autogenerate", 
                    "-m", "Initial migration - test"
                ])
                
                if not success:
                    self.log_result("Создание миграции", False, stderr)
                    return False
                
                print("✅ Первая миграция создана")
            else:
                print(f"✅ Найдено миграций: {len(revisions)}")
            
            self.log_result("Создание миграции", True)
            return True
            
        except Exception as e:
            self.log_result("Создание миграции", False, str(e))
            return False
    
    def test_migration_application(self) -> bool:
        """Тест 5: Применение миграций"""
        print("🔄 Тест 5: Применение миграций...")
        
        try:
            # Применяем миграции
            success, stdout, stderr = self.run_command([
                "alembic", "upgrade", "head"
            ])
            
            if not success:
                self.log_result("Применение миграций", False, stderr)
                return False
            
            # Проверяем текущую версию
            success, stdout, stderr = self.run_command([
                "alembic", "current"
            ])
            
            if success and stdout.strip():
                print(f"✅ Миграции применены, текущая версия: {stdout.strip()}")
                self.log_result("Применение миграций", True)
                return True
            else:
                self.log_result("Применение миграций", False, "Версия миграции не определена")
                return False
            
        except Exception as e:
            self.log_result("Применение миграций", False, str(e))
            return False
    
    def test_database_tables(self) -> bool:
        """Тест 6: Проверка созданных таблиц"""
        print("🔄 Тест 6: Проверка созданных таблиц...")
        
        try:
            from src.core.config import get_settings
            settings = get_settings()
            engine = create_engine(settings.database_url)
            
            expected_tables = [
                'users', 'sellers', 'user_profiles', 'seller_settings',
                'messages', 'conversations', 'message_templates',
                'alembic_version'
            ]
            
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                existing_tables = [row[0] for row in result.fetchall()]
            
            missing_tables = set(expected_tables) - set(existing_tables)
            
            if missing_tables:
                self.log_result("Таблицы БД", False, f"Отсутствуют таблицы: {missing_tables}")
                return False
            
            print(f"✅ Все таблицы созданы: {len(existing_tables)} таблиц")
            self.log_result("Таблицы БД", True)
            return True
            
        except Exception as e:
            self.log_result("Таблицы БД", False, str(e))
            return False
    
    def test_fastapi_import(self) -> bool:
        """Тест 7: Импорт FastAPI приложения"""
        print("🔄 Тест 7: Импорт FastAPI приложения...")
        
        try:
            # Пытаемся импортировать основное приложение
            from src.api.main import app
            
            # Проверяем наличие роутов
            routes_count = len(app.routes)
            if routes_count == 0:
                self.log_result("FastAPI импорт", False, "Нет зарегистрированных роутов")
                return False
            
            print(f"✅ FastAPI приложение загружено, роутов: {routes_count}")
            self.log_result("FastAPI импорт", True)
            return True
            
        except Exception as e:
            self.log_result("FastAPI импорт", False, str(e))
            return False
    
    def test_api_server_start(self) -> bool:
        """Тест 8: Запуск API сервера"""
        print("🔄 Тест 8: Запуск API сервера...")
        
        try:
            # Запускаем сервер в фоновом режиме
            server_process = subprocess.Popen([
                sys.executable, "-m", "uvicorn",
                "src.api.main:app",
                "--host", "127.0.0.1",
                "--port", "8001",  # Используем другой порт для тестов
                "--log-level", "error"
            ], cwd=self.project_root)
            
            # Ждем запуска сервера
            time.sleep(5)
            
            try:
                # Проверяем health check
                response = requests.get("http://127.0.0.1:8001/health", timeout=10)
                
                if response.status_code == 200:
                    print("✅ API сервер запущен и отвечает")
                    self.log_result("Запуск API", True)
                    result = True
                else:
                    print(f"❌ API сервер вернул код: {response.status_code}")
                    self.log_result("Запуск API", False, f"HTTP {response.status_code}")
                    result = False
                    
            except requests.RequestException as e:
                print(f"❌ Ошибка запроса к API: {e}")
                self.log_result("Запуск API", False, str(e))
                result = False
            
            finally:
                # Останавливаем сервер
                server_process.terminate()
                server_process.wait(timeout=10)
            
            return result
            
        except Exception as e:
            self.log_result("Запуск API", False, str(e))
            return False
    
    def test_core_components(self) -> bool:
        """Тест 9: Тестирование основных компонентов"""
        print("🔄 Тест 9: Тестирование основных компонентов...")
        
        try:
            # Тестируем импорт всех модулей
            modules_to_test = [
                "src.core.config",
                "src.core.ai_consultant",
                "src.integrations.avito.api_client",
                "src.integrations.gemini.client",
                "src.database.models",
                "src.services.auth_service",
                "src.services.user_service",
            ]
            
            failed_imports = []
            for module in modules_to_test:
                try:
                    __import__(module)
                except ImportError as e:
                    failed_imports.append(f"{module}: {e}")
            
            if failed_imports:
                self.log_result("Импорт компонентов", False, "; ".join(failed_imports))
                return False
            
            print(f"✅ Все основные компоненты импортируются: {len(modules_to_test)} модулей")
            self.log_result("Импорт компонентов", True)
            return True
            
        except Exception as e:
            self.log_result("Импорт компонентов", False, str(e))
            return False
    
    def run_complete_test(self) -> bool:
        """Запустить полное тестирование"""
        print("🧪 ПОЛНОЕ ТЕСТИРОВАНИЕ НАСТРОЙКИ AVITO AI BOT")
        print("=" * 60)
        
        tests = [
            ("Окружение", self.test_environment_setup),
            ("База данных", self.test_database_connection),
            ("Инициализация миграций", self.test_migrations_initialization),
            ("Создание миграции", self.test_migration_creation),
            ("Применение миграций", self.test_migration_application),
            ("Таблицы БД", self.test_database_tables),
            ("FastAPI импорт", self.test_fastapi_import),
            ("Запуск API", self.test_api_server_start),
            ("Основные компоненты", self.test_core_components),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n📋 {test_name}...")
            try:
                success = test_func()
                if success:
                    passed += 1
                    print(f"✅ {test_name} - ПРОЙДЕН")
                else:
                    print(f"❌ {test_name} - ПРОВАЛ")
                    # Продолжаем тестирование даже после ошибок
            except Exception as e:
                print(f"❌ {test_name} - ОШИБКА: {e}")
                self.log_result(test_name, False, str(e))
        
        # Показываем результаты
        print("\n" + "=" * 60)
        print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
        
        for test_name, _ in tests:
            if test_name in self.results:
                status = "✅ ПРОЙДЕН" if self.results[test_name] else "❌ ПРОВАЛ"
                print(f"   {test_name}: {status}")
        
        print(f"\n🎯 ИТОГО: {passed}/{total} тестов пройдено")
        
        if self.errors:
            print(f"\n❌ ОШИБКИ:")
            for error in self.errors[:5]:  # Показываем только первые 5 ошибок
                print(f"   - {error}")
            if len(self.errors) > 5:
                print(f"   ... и еще {len(self.errors) - 5} ошибок")
        
        if passed == total:
            print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Система готова к работе!")
            print("\n📋 Следующие шаги:")
            print("1. Заполните API ключи в .env файле")
            print("2. Запустите сервер: uvicorn src.api.main:app --reload")
            print("3. Откройте документацию: http://localhost:8000/docs")
            return True
        else:
            print(f"\n⚠️ {total - passed} тестов провалились. Требуется исправление.")
            return False


def main():
    """Главная функция"""
    try:
        tester = CompleteSetupTester()
        success = tester.run_complete_test()
        
        if success:
            print("\n✅ Тестирование завершено успешно")
            sys.exit(0)
        else:
            print("\n❌ Тестирование завершено с ошибками")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()