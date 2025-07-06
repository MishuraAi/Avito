#!/usr/bin/env python3
"""
🔍 Скрипт проверки подключения к базе данных

Этот скрипт проверяет:
1. Подключение к базе данных (SQLite/PostgreSQL)
2. Существование базы данных
3. Права доступа пользователя
4. Готовность к применению миграций
"""

import os
import sys
from pathlib import Path
import asyncio
from typing import Optional

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from sqlalchemy import create_engine, text, inspect
    from sqlalchemy.exc import OperationalError, ProgrammingError
    from src.core.config import get_settings
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("📝 Убедитесь что установлены все зависимости: pip install -r requirements-dev.txt")
    sys.exit(1)


class DatabaseChecker:
    """Класс для проверки состояния базы данных"""
    
    def __init__(self):
        self.settings = None
        self.engine = None
        
    def load_settings(self) -> bool:
        """Загрузить настройки из .env файла"""
        try:
            self.settings = get_settings()
            print(f"✅ Настройки загружены из окружения")
            print(f"📍 DATABASE_URL: {self._mask_url(self.settings.database_url)}")
            return True
        except Exception as e:
            print(f"❌ Ошибка загрузки настроек: {e}")
            print("📝 Проверьте наличие .env файла и правильность настроек")
            return False
    
    def _mask_url(self, url: str) -> str:
        """Замаскировать пароль в URL для безопасного вывода"""
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
    
    def test_connection(self) -> bool:
        """Проверить базовое подключение к базе данных"""
        try:
            self.engine = create_engine(self.settings.database_url)
            
            with self.engine.connect() as conn:
                # Определяем тип БД и выполняем соответствующую команду
                if "sqlite" in self.settings.database_url.lower():
                    result = conn.execute(text("SELECT sqlite_version()"))
                    version = f"SQLite {result.fetchone()[0]}"
                    db_type = "SQLite"
                elif "postgresql" in self.settings.database_url.lower():
                    result = conn.execute(text("SELECT version()"))
                    version = result.fetchone()[0]
                    db_type = "PostgreSQL"
                else:
                    # Для других БД пробуем простой запрос
                    conn.execute(text("SELECT 1"))
                    version = "Unknown version"
                    db_type = "Database"
                
            print(f"✅ Подключение к {db_type} успешно")
            print(f"📊 Версия: {version}")
            return True
            
        except OperationalError as e:
            print(f"❌ Ошибка подключения к базе данных:")
            print(f"   {e}")
            print("\n📋 Возможные причины:")
            if "sqlite" in self.settings.database_url.lower():
                print("1. Нет прав на создание файла БД")
                print("2. Неправильный путь к файлу БД")
                print("3. Диск переполнен")
            else:
                print("1. PostgreSQL не запущен")
                print("2. Неправильные учетные данные")
                print("3. База данных не существует")
                print("4. Неправильный хост или порт")
            return False
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            return False
    
    def check_database_exists(self) -> bool:
        """Проверить существование базы данных"""
        try:
            # Для SQLite файл создается автоматически при подключении
            if "sqlite" in self.settings.database_url.lower():
                with self.engine.connect() as conn:
                    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                    tables = result.fetchall()
                
                print(f"✅ SQLite база данных создана/доступна")
                if tables:
                    print(f"📋 Найдено таблиц: {len(tables)}")
                else:
                    print("ℹ️ База данных пуста (нет таблиц)")
                return True
            
            # Для PostgreSQL проверяем имя БД
            else:
                db_url = self.settings.database_url
                db_name = db_url.split("/")[-1].split("?")[0]
                
                with self.engine.connect() as conn:
                    result = conn.execute(text("SELECT current_database()"))
                    current_db = result.fetchone()[0]
                    
                if current_db == db_name:
                    print(f"✅ База данных '{db_name}' существует и доступна")
                    return True
                else:
                    print(f"⚠️ Подключились к '{current_db}', ожидали '{db_name}'")
                    return False
                
        except Exception as e:
            print(f"❌ Ошибка проверки базы данных: {e}")
            return False
    
    def check_user_permissions(self) -> bool:
        """Проверить права пользователя"""
        try:
            # Для SQLite нет понятия пользователей, проверяем возможность записи
            if "sqlite" in self.settings.database_url.lower():
                with self.engine.connect() as conn:
                    # Пробуем создать временную таблицу
                    conn.execute(text("""
                        CREATE TEMPORARY TABLE test_permissions (id INTEGER)
                    """))
                    conn.execute(text("DROP TABLE test_permissions"))
                    
                print(f"✅ SQLite: права на запись и создание таблиц есть")
                return True
            
            # Для PostgreSQL проверяем права CREATE
            else:
                with self.engine.connect() as conn:
                    result = conn.execute(text("""
                        SELECT has_database_privilege(current_user, current_database(), 'CREATE')
                    """))
                    can_create = result.fetchone()[0]
                    
                    result = conn.execute(text("SELECT current_user"))
                    current_user = result.fetchone()[0]
                    
                if can_create:
                    print(f"✅ Пользователь '{current_user}' имеет права CREATE")
                    return True
                else:
                    print(f"❌ Пользователь '{current_user}' НЕ имеет права CREATE")
                    print("📝 Выдайте права: GRANT ALL PRIVILEGES ON DATABASE db_name TO user_name;")
                    return False
                
        except Exception as e:
            print(f"❌ Ошибка проверки прав: {e}")
            return False
    
    def check_tables(self) -> bool:
        """Проверить существующие таблицы"""
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            
            if tables:
                print(f"📋 Найдено таблиц в БД: {len(tables)}")
                for table in sorted(tables):
                    print(f"   - {table}")
                    
                # Проверяем наличие таблицы alembic_version
                if 'alembic_version' in tables:
                    with self.engine.connect() as conn:
                        result = conn.execute(text("SELECT version_num FROM alembic_version"))
                        version = result.fetchone()
                        if version:
                            print(f"📊 Текущая версия миграций: {version[0]}")
                        else:
                            print("⚠️ Таблица alembic_version пуста")
                else:
                    print("ℹ️ Таблица alembic_version не найдена (миграции не применялись)")
            else:
                print("ℹ️ База данных пуста (таблицы не найдены)")
                
            return True
            
        except Exception as e:
            print(f"❌ Ошибка проверки таблиц: {e}")
            return False
    
    def test_crud_operations(self) -> bool:
        """Проверить основные CRUD операции"""
        try:
            with self.engine.connect() as conn:
                # Определяем тип БД и используем соответствующий синтаксис
                if "sqlite" in self.settings.database_url.lower():
                    # SQLite синтаксис
                    conn.execute(text("""
                        CREATE TEMPORARY TABLE test_table (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                else:
                    # PostgreSQL синтаксис
                    conn.execute(text("""
                        CREATE TEMPORARY TABLE test_table (
                            id SERIAL PRIMARY KEY,
                            name VARCHAR(50),
                            created_at TIMESTAMP DEFAULT NOW()
                        )
                    """))
                
                # Вставляем данные
                conn.execute(text("""
                    INSERT INTO test_table (name) VALUES ('test')
                """))
                
                # Читаем данные
                result = conn.execute(text("SELECT name FROM test_table WHERE name = 'test'"))
                row = result.fetchone()
                
                if not row:
                    raise Exception("Не удалось вставить или прочитать данные")
                
                # Обновляем данные
                conn.execute(text("""
                    UPDATE test_table SET name = 'updated' WHERE name = 'test'
                """))
                
                # Проверяем обновление
                result = conn.execute(text("SELECT name FROM test_table WHERE name = 'updated'"))
                updated_row = result.fetchone()
                
                if not updated_row:
                    raise Exception("Не удалось обновить данные")
                
                # Удаляем данные
                conn.execute(text("DELETE FROM test_table WHERE name = 'updated'"))
                
                # Проверяем удаление
                result = conn.execute(text("SELECT COUNT(*) FROM test_table"))
                count = result.fetchone()[0]
                
                if count != 0:
                    raise Exception("Не удалось удалить данные")
                
                conn.commit()
                
            print("✅ CRUD операции выполняются успешно")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка CRUD операций: {e}")
            return False
    
    def run_full_check(self) -> bool:
        """Запустить полную проверку базы данных"""
        print("🔍 Полная проверка базы данных")
        print("=" * 50)
        
        checks = [
            ("Загрузка настроек", self.load_settings),
            ("Подключение к базе данных", self.test_connection),
            ("Существование базы данных", self.check_database_exists),
            ("Права пользователя", self.check_user_permissions),
            ("Существующие таблицы", self.check_tables),
            ("CRUD операции", self.test_crud_operations),
        ]
        
        results = []
        for name, check_func in checks:
            print(f"\n🔄 {name}...")
            try:
                result = check_func()
                results.append(result)
                if not result:
                    print(f"❌ {name} - ПРОВАЛ")
                    break
            except Exception as e:
                print(f"❌ {name} - ОШИБКА: {e}")
                results.append(False)
                break
        
        print("\n" + "=" * 50)
        print("📊 РЕЗУЛЬТАТЫ ПРОВЕРКИ:")
        
        passed = sum(results)
        total = len(results)
        
        for i, (name, _) in enumerate(checks[:len(results)]):
            status = "✅ ПРОЙДЕН" if results[i] else "❌ ПРОВАЛ"
            print(f"   {name}: {status}")
        
        print(f"\n🎯 Итого: {passed}/{total} проверок пройдено")
        
        if passed == total:
            print("🎉 База данных готова к работе!")
            print("\n📋 Следующие шаги:")
            print("1. Запустите инициализацию миграций: python scripts/init_migrations.py")
            print("2. Примените миграции: alembic upgrade head")
            print("3. Запустите приложение: uvicorn src.api.main:app --reload")
            return True
        else:
            print("⚠️ Требуется устранить проблемы перед продолжением")
            return False


def main():
    """Главная функция"""
    try:
        checker = DatabaseChecker()
        success = checker.run_full_check()
        
        if success:
            print("\n✅ Проверка завершена успешно")
            sys.exit(0)
        else:
            print("\n❌ Проверка завершена с ошибками")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Проверка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()