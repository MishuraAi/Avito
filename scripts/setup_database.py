#!/usr/bin/env python3
"""
🛠️ Скрипт настройки базы данных PostgreSQL

Этот скрипт:
1. Создает пользователя PostgreSQL
2. Создает базу данных
3. Выдает необходимые права
4. Настраивает тестовую базу данных
"""

import os
import sys
import subprocess
import getpass
from pathlib import Path
from typing import Optional

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("❌ Модуль psycopg2 не установлен")
    print("📝 Установите: pip install psycopg2-binary")
    sys.exit(1)


class DatabaseSetup:
    """Класс для настройки базы данных PostgreSQL"""
    
    def __init__(self):
        self.admin_user = "postgres"
        self.admin_password = None
        self.admin_host = "localhost"
        self.admin_port = "5432"
        
        # Настройки для нашего проекта
        self.project_user = "avito_user"
        self.project_password = "avito_password"
        self.project_db = "avito_ai_db"
        self.test_db = "avito_ai_test_db"
    
    def get_admin_credentials(self):
        """Получить учетные данные администратора PostgreSQL"""
        print("🔐 Введите учетные данные администратора PostgreSQL")
        print(f"👤 Пользователь (по умолчанию: {self.admin_user}): ", end="")
        
        user_input = input().strip()
        if user_input:
            self.admin_user = user_input
        
        print(f"🌐 Хост (по умолчанию: {self.admin_host}): ", end="")
        host_input = input().strip()
        if host_input:
            self.admin_host = host_input
        
        print(f"🔌 Порт (по умолчанию: {self.admin_port}): ", end="")
        port_input = input().strip()
        if port_input:
            self.admin_port = port_input
        
        self.admin_password = getpass.getpass(f"🔑 Пароль для {self.admin_user}: ")
        
        if not self.admin_password:
            print("❌ Пароль не может быть пустым")
            return False
        
        return True
    
    def test_admin_connection(self) -> bool:
        """Проверить подключение с правами администратора"""
        try:
            conn = psycopg2.connect(
                host=self.admin_host,
                port=self.admin_port,
                user=self.admin_user,
                password=self.admin_password,
                database="postgres"  # Подключаемся к системной БД
            )
            
            with conn.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
            
            conn.close()
            print(f"✅ Подключение к PostgreSQL успешно")
            print(f"📊 Версия: {version}")
            return True
            
        except psycopg2.Error as e:
            print(f"❌ Ошибка подключения: {e}")
            return False
    
    def user_exists(self, username: str) -> bool:
        """Проверить существование пользователя"""
        try:
            conn = psycopg2.connect(
                host=self.admin_host,
                port=self.admin_port,
                user=self.admin_user,
                password=self.admin_password,
                database="postgres"
            )
            
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM pg_roles WHERE rolname = %s",
                    (username,)
                )
                exists = cursor.fetchone() is not None
            
            conn.close()
            return exists
            
        except psycopg2.Error as e:
            print(f"❌ Ошибка проверки пользователя: {e}")
            return False
    
    def database_exists(self, dbname: str) -> bool:
        """Проверить существование базы данных"""
        try:
            conn = psycopg2.connect(
                host=self.admin_host,
                port=self.admin_port,
                user=self.admin_user,
                password=self.admin_password,
                database="postgres"
            )
            
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (dbname,)
                )
                exists = cursor.fetchone() is not None
            
            conn.close()
            return exists
            
        except psycopg2.Error as e:
            print(f"❌ Ошибка проверки базы данных: {e}")
            return False
    
    def create_user(self) -> bool:
        """Создать пользователя для проекта"""
        try:
            if self.user_exists(self.project_user):
                print(f"ℹ️ Пользователь '{self.project_user}' уже существует")
                return True
            
            conn = psycopg2.connect(
                host=self.admin_host,
                port=self.admin_port,
                user=self.admin_user,
                password=self.admin_password,
                database="postgres"
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    CREATE USER {self.project_user} 
                    WITH PASSWORD '{self.project_password}'
                    CREATEDB
                """)
            
            conn.close()
            print(f"✅ Пользователь '{self.project_user}' создан")
            return True
            
        except psycopg2.Error as e:
            print(f"❌ Ошибка создания пользователя: {e}")
            return False
    
    def create_database(self, dbname: str) -> bool:
        """Создать базу данных"""
        try:
            if self.database_exists(dbname):
                print(f"ℹ️ База данных '{dbname}' уже существует")
                return True
            
            conn = psycopg2.connect(
                host=self.admin_host,
                port=self.admin_port,
                user=self.admin_user,
                password=self.admin_password,
                database="postgres"
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    CREATE DATABASE {dbname}
                    OWNER {self.project_user}
                    ENCODING 'UTF8'
                    LC_COLLATE = 'en_US.UTF-8'
                    LC_CTYPE = 'en_US.UTF-8'
                """)
            
            conn.close()
            print(f"✅ База данных '{dbname}' создана")
            return True
            
        except psycopg2.Error as e:
            print(f"❌ Ошибка создания базы данных '{dbname}': {e}")
            return False
    
    def grant_privileges(self, dbname: str) -> bool:
        """Выдать права на базу данных"""
        try:
            conn = psycopg2.connect(
                host=self.admin_host,
                port=self.admin_port,
                user=self.admin_user,
                password=self.admin_password,
                database="postgres"
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    GRANT ALL PRIVILEGES ON DATABASE {dbname} TO {self.project_user}
                """)
            
            conn.close()
            print(f"✅ Права на '{dbname}' выданы пользователю '{self.project_user}'")
            return True
            
        except psycopg2.Error as e:
            print(f"❌ Ошибка выдачи прав: {e}")
            return False
    
    def test_project_connection(self, dbname: str) -> bool:
        """Проверить подключение от имени проектного пользователя"""
        try:
            conn = psycopg2.connect(
                host=self.admin_host,
                port=self.admin_port,
                user=self.project_user,
                password=self.project_password,
                database=dbname
            )
            
            with conn.cursor() as cursor:
                cursor.execute("SELECT current_user, current_database()")
                user, db = cursor.fetchone()
            
            conn.close()
            print(f"✅ Подключение к '{db}' от пользователя '{user}' успешно")
            return True
            
        except psycopg2.Error as e:
            print(f"❌ Ошибка подключения: {e}")
            return False
    
    def create_env_file(self) -> bool:
        """Создать .env файл с правильными настройками"""
        try:
            env_path = project_root / ".env"
            
            if env_path.exists():
                response = input("📄 Файл .env уже существует. Перезаписать? (y/n): ").lower().strip()
                if response != 'y':
                    print("ℹ️ Файл .env не изменен")
                    return True
            
            database_url = f"postgresql://{self.project_user}:{self.project_password}@{self.admin_host}:{self.admin_port}/{self.project_db}"
            test_database_url = f"postgresql://{self.project_user}:{self.project_password}@{self.admin_host}:{self.admin_port}/{self.test_db}"
            
            env_content = f"""# 🔧 Конфигурация Avito AI Bot
# Автоматически сгенерирован scripts/setup_database.py

# Основные настройки
DEBUG=True
ENVIRONMENT=development
SECRET_KEY=change-this-secret-key-in-production
JWT_SECRET_KEY=change-this-jwt-secret-key-too
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# База данных
DATABASE_URL={database_url}
TEST_DATABASE_URL={test_database_url}

# Redis
REDIS_URL=redis://localhost:6379/0

# API ключи (ОБЯЗАТЕЛЬНО ЗАПОЛНИТЕ!)
GEMINI_API_KEY=your-gemini-api-key-here
AVITO_CLIENT_ID=your-avito-client-id
AVITO_CLIENT_SECRET=your-avito-client-secret

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Логирование
LOG_LEVEL=INFO
LOG_FILE_PATH=data/logs/app.log

# Rate limiting
RATE_LIMIT_FREE_REQUESTS_PER_MINUTE=10
RATE_LIMIT_PREMIUM_REQUESTS_PER_MINUTE=100

# Сервер
SERVER_PORT=8000
SERVER_HOST=0.0.0.0
"""
            
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(env_content)
            
            print(f"✅ Файл .env создан: {env_path}")
            print("⚠️ ВАЖНО: Замените API ключи на реальные!")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания .env файла: {e}")
            return False
    
    def run_setup(self) -> bool:
        """Запустить полную настройку базы данных"""
        print("🛠️ Настройка базы данных PostgreSQL для Avito AI Bot")
        print("=" * 60)
        
        # 1. Получаем учетные данные администратора
        if not self.get_admin_credentials():
            return False
        
        # 2. Проверяем подключение
        print(f"\n🔄 Проверка подключения к PostgreSQL...")
        if not self.test_admin_connection():
            return False
        
        # 3. Создаем пользователя
        print(f"\n🔄 Создание пользователя '{self.project_user}'...")
        if not self.create_user():
            return False
        
        # 4. Создаем основную базу данных
        print(f"\n🔄 Создание базы данных '{self.project_db}'...")
        if not self.create_database(self.project_db):
            return False
        
        # 5. Создаем тестовую базу данных
        print(f"\n🔄 Создание тестовой базы данных '{self.test_db}'...")
        if not self.create_database(self.test_db):
            return False
        
        # 6. Выдаем права
        print(f"\n🔄 Выдача прав на базы данных...")
        if not self.grant_privileges(self.project_db):
            return False
        if not self.grant_privileges(self.test_db):
            return False
        
        # 7. Тестируем подключение
        print(f"\n🔄 Тестирование подключения...")
        if not self.test_project_connection(self.project_db):
            return False
        if not self.test_project_connection(self.test_db):
            return False
        
        # 8. Создаем .env файл
        print(f"\n🔄 Создание .env файла...")
        if not self.create_env_file():
            return False
        
        print("\n" + "=" * 60)
        print("🎉 Настройка базы данных завершена успешно!")
        print("\n📋 Созданные ресурсы:")
        print(f"   👤 Пользователь: {self.project_user}")
        print(f"   🗄️ Основная БД: {self.project_db}")
        print(f"   🧪 Тестовая БД: {self.test_db}")
        print(f"   📄 Конфигурация: .env")
        
        print(f"\n📋 Следующие шаги:")
        print("1. Отредактируйте .env файл (добавьте API ключи)")
        print("2. Проверьте подключение: python scripts/check_database.py")
        print("3. Инициализируйте миграции: python scripts/init_migrations.py")
        print("4. Примените миграции: alembic upgrade head")
        
        return True


def main():
    """Главная функция"""
    try:
        setup = DatabaseSetup()
        success = setup.run_setup()
        
        if success:
            print("\n✅ Настройка завершена успешно")
            sys.exit(0)
        else:
            print("\n❌ Настройка завершена с ошибками")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Настройка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()