#!/usr/bin/env python3
"""
🐳 Скрипт настройки Docker окружения для Avito AI Bot

Этот скрипт:
1. Проверяет установку Docker и Docker Compose
2. Создает необходимые директории
3. Генерирует секретные ключи
4. Настраивает файлы конфигурации
5. Запускает контейнеры
"""

import os
import sys
import subprocess
import secrets
import string
from pathlib import Path
from typing import Dict, List, Optional

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class DockerSetup:
    """Класс для настройки Docker окружения"""
    
    def __init__(self):
        self.project_root = project_root
        self.docker_dir = self.project_root / "docker"
        self.secrets_dir = self.project_root / "secrets"
        self.execution_stats = {
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
    
    def check_docker_installation(self) -> bool:
        """Проверка установки Docker и Docker Compose"""
        try:
            print("🔍 Проверка установки Docker...")
            
            # Проверяем Docker
            result = subprocess.run(
                ["docker", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode != 0:
                print("❌ Docker не установлен!")
                print("📦 Установите Docker: https://docs.docker.com/get-docker/")
                return False
            
            docker_version = result.stdout.strip()
            print(f"✅ {docker_version}")
            
            # Проверяем Docker Compose
            # Сначала пробуем новую команду
            result = subprocess.run(
                ["docker", "compose", "version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode != 0:
                # Если новая команда не работает, пробуем старую
                result = subprocess.run(
                    ["docker-compose", "--version"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                
                if result.returncode != 0:
                    print("❌ Docker Compose не установлен!")
                    print("📦 Установите Docker Compose: https://docs.docker.com/compose/install/")
                    return False
                
                compose_version = result.stdout.strip()
                print(f"✅ {compose_version} (legacy)")
                self.compose_command = ["docker-compose"]
            else:
                compose_version = result.stdout.strip()
                print(f"✅ {compose_version}")
                self.compose_command = ["docker", "compose"]
            
            # Проверяем что Docker daemon запущен
            result = subprocess.run(
                ["docker", "info"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode != 0:
                print("❌ Docker daemon не запущен!")
                print("🚀 Запустите Docker Desktop или Docker daemon")
                return False
            
            print("✅ Docker daemon запущен")
            self.log_step("Docker установлен и работает", True)
            return True
            
        except subprocess.TimeoutExpired:
            print("❌ Таймаут при проверке Docker")
            return False
        except FileNotFoundError:
            print("❌ Docker не найден в PATH")
            print("📦 Установите Docker: https://docs.docker.com/get-docker/")
            return False
        except Exception as e:
            print(f"❌ Ошибка проверки Docker: {e}")
            return False
    
    def create_directories(self) -> bool:
        """Создание необходимых директорий"""
        try:
            print("📁 Создание директорий...")
            
            directories = [
                self.docker_dir,
                self.docker_dir / "nginx",
                self.docker_dir / "postgres",
                self.docker_dir / "redis", 
                self.docker_dir / "init-scripts",
                self.secrets_dir,
                self.project_root / "data" / "logs",
                self.project_root / "data" / "uploads",
                self.project_root / "data" / "cache"
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                print(f"   📂 {directory.relative_to(self.project_root)}")
            
            self.log_step("Директории созданы", True)
            return True
            
        except Exception as e:
            self.log_step("Ошибка создания директорий", False)
            print(f"   Детали: {e}")
            return False
    
    def generate_secrets(self) -> bool:
        """Генерация секретных ключей"""
        try:
            print("🔐 Генерация секретных ключей...")
            
            def generate_key(length=32) -> str:
                """Генерация случайного ключа"""
                alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                return ''.join(secrets.choice(alphabet) for _ in range(length))
            
            secrets_config = {
                "secret_key.txt": generate_key(64),
                "jwt_secret_key.txt": generate_key(64),
                "postgres_password.txt": generate_key(32),
                "redis_password.txt": generate_key(32),
                "grafana_password.txt": generate_key(16),
                # Заглушки для API ключей (пользователь должен заполнить)
                "gemini_api_key.txt": "REPLACE_WITH_YOUR_REAL_GEMINI_API_KEY",
                "avito_client_id.txt": "REPLACE_WITH_YOUR_REAL_AVITO_CLIENT_ID", 
                "avito_client_secret.txt": "REPLACE_WITH_YOUR_REAL_AVITO_CLIENT_SECRET",
                "sentry_dsn.txt": "REPLACE_WITH_YOUR_SENTRY_DSN_OR_LEAVE_EMPTY"
            }
            
            created_files = []
            for filename, content in secrets_config.items():
                secret_file = self.secrets_dir / filename
                
                if not secret_file.exists():
                    secret_file.write_text(content, encoding='utf-8')
                    created_files.append(filename)
                    print(f"   🔑 {filename}")
                else:
                    print(f"   ℹ️ {filename} (уже существует)")
            
            if created_files:
                print(f"\n⚠️ ВАЖНО: Замените заглушки API ключей в папке secrets/")
                print("   📝 Особенно важны:")
                print("      - gemini_api_key.txt")
                print("      - avito_client_id.txt") 
                print("      - avito_client_secret.txt")
            
            self.log_step("Секретные ключи сгенерированы", True)
            return True
            
        except Exception as e:
            self.log_step("Ошибка генерации ключей", False)
            print(f"   Детали: {e}")
            return False
    
    def create_env_file(self) -> bool:
        """Создание .env файла для Docker"""
        try:
            print("📄 Создание .env файла...")
            
            env_file = self.project_root / ".env"
            
            if env_file.exists():
                response = input("❓ Файл .env существует. Перезаписать? (y/n): ").lower().strip()
                if response != 'y':
                    print("ℹ️ Файл .env не изменен")
                    self.log_step("Файл .env пропущен", True)
                    return True
            
            # Читаем пароли из созданных файлов
            try:
                postgres_password = (self.secrets_dir / "postgres_password.txt").read_text().strip()
                redis_password = (self.secrets_dir / "redis_password.txt").read_text().strip()
                secret_key = (self.secrets_dir / "secret_key.txt").read_text().strip()
                jwt_secret_key = (self.secrets_dir / "jwt_secret_key.txt").read_text().strip()
                grafana_password = (self.secrets_dir / "grafana_password.txt").read_text().strip()
            except Exception as e:
                print(f"⚠️ Ошибка чтения секретов: {e}")
                postgres_password = "generate_new_password"
                redis_password = "generate_new_password"
                secret_key = "generate_new_secret"
                jwt_secret_key = "generate_new_jwt_secret"
                grafana_password = "admin123"
            
            env_content = f"""# 🐳 Переменные окружения для Docker Compose
# Автоматически сгенерирован scripts/setup_docker.py

# ===== ОСНОВНЫЕ НАСТРОЙКИ =====
ENVIRONMENT=development
DEBUG=true

# ===== БЕЗОПАСНОСТЬ =====
SECRET_KEY={secret_key}
JWT_SECRET_KEY={jwt_secret_key}

# ===== БАЗА ДАННЫХ =====
POSTGRES_PASSWORD={postgres_password}

# ===== REDIS =====
REDIS_PASSWORD={redis_password}

# ===== API КЛЮЧИ (ОБЯЗАТЕЛЬНО ЗАМЕНИТЕ!) =====
GEMINI_API_KEY=your-real-gemini-api-key-here
AVITO_CLIENT_ID=your-real-avito-client-id-here
AVITO_CLIENT_SECRET=your-real-avito-client-secret-here

# ===== МОНИТОРИНГ =====
SENTRY_DSN=
GRAFANA_PASSWORD={grafana_password}

# ===== ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ =====
LOG_LEVEL=INFO
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
"""
            
            env_file.write_text(env_content, encoding='utf-8')
            
            print("✅ Файл .env создан")
            print("⚠️ ОБЯЗАТЕЛЬНО замените API ключи на реальные!")
            
            self.log_step("Файл .env создан", True)
            return True
            
        except Exception as e:
            self.log_step("Ошибка создания .env", False)
            print(f"   Детали: {e}")
            return False
    
    def fix_alembic_ini(self) -> bool:
        """Исправление проблемы с alembic.ini"""
        try:
            print("🔧 Исправление alembic.ini...")
            
            alembic_ini = self.project_root / "alembic.ini"
            
            if not alembic_ini.exists():
                print("⚠️ alembic.ini не найден, пропускаем")
                self.log_step("alembic.ini не требует исправления", True)
                return True
            
            # Читаем содержимое
            content = alembic_ini.read_text(encoding='utf-8')
            
            # Проверяем наличие дублирующихся настроек
            if content.count('sqlalchemy.url') > 1:
                print("🔍 Обнаружены дублирующиеся настройки sqlalchemy.url")
                
                # Создаем исправленную версию
                fixed_content = """# Конфигурация Alembic для Avito AI Responder
# Исправлено для Docker

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
                backup_file = alembic_ini.with_suffix('.ini.backup')
                backup_file.write_text(content, encoding='utf-8')
                print(f"📋 Создан бэкап: {backup_file.name}")
                
                # Записываем исправленную версию
                alembic_ini.write_text(fixed_content, encoding='utf-8')
                print("✅ alembic.ini исправлен")
            else:
                print("ℹ️ alembic.ini в порядке")
            
            self.log_step("alembic.ini проверен/исправлен", True)
            return True
            
        except Exception as e:
            self.log_step("Ошибка исправления alembic.ini", False)
            print(f"   Детали: {e}")
            return False
    
    def create_nginx_config(self) -> bool:
        """Создание конфигурации Nginx"""
        try:
            print("🌐 Создание конфигурации Nginx...")
            
            # Конфигурация для разработки
            dev_config = self.docker_dir / "nginx" / "dev.conf"
            dev_content = """# Nginx конфигурация для разработки
server {
    listen 80;
    server_name localhost;
    
    client_max_body_size 10M;
    
    # Проксирование на приложение
    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket поддержка для hot reload
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Health check
    location /nginx-health {
        access_log off;
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }
}
"""
            
            dev_config.write_text(dev_content, encoding='utf-8')
            print("   📄 dev.conf создан")
            
            # Конфигурация для продакшена
            prod_config = self.docker_dir / "nginx" / "prod.conf"
            prod_content = """# Nginx конфигурация для продакшена
upstream app_servers {
    server app:8000;
    # Для load balancing добавьте больше серверов
    # server app2:8000;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL configuration
    ssl_certificate /etc/ssl/certs/fullchain.pem;
    ssl_certificate_key /etc/ssl/certs/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    
    client_max_body_size 10M;
    
    # Проксирование на приложение
    location / {
        proxy_pass http://app_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Таймауты
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Статические файлы (если будут)
    location /static/ {
        alias /app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Health check
    location /nginx-health {
        access_log off;
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }
}
"""
            
            prod_config.write_text(prod_content, encoding='utf-8')
            print("   📄 prod.conf создан")
            
            self.log_step("Конфигурация Nginx создана", True)
            return True
            
        except Exception as e:
            self.log_step("Ошибка создания конфигурации Nginx", False)
            print(f"   Детали: {e}")
            return False
    
    def test_docker_setup(self) -> bool:
        """Тестирование Docker setup"""
        try:
            print("🧪 Тестирование Docker конфигурации...")
            
            # Проверяем docker-compose.yml
            compose_file = self.project_root / "docker-compose.yml"
            if not compose_file.exists():
                print("❌ docker-compose.yml не найден!")
                return False
            
            # Валидируем docker-compose файл
            result = subprocess.run(
                self.compose_command + ["config", "-f", str(compose_file)],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print("❌ Ошибка в docker-compose.yml:")
                print(result.stderr)
                return False
            
            print("✅ docker-compose.yml валиден")
            
            # Проверяем Dockerfile
            dockerfile = self.project_root / "Dockerfile"
            if not dockerfile.exists():
                print("⚠️ Dockerfile не найден")
                return False
            
            print("✅ Dockerfile найден")
            
            self.log_step("Docker конфигурация протестирована", True)
            return True
            
        except Exception as e:
            self.log_step("Ошибка тестирования Docker", False)
            print(f"   Детали: {e}")
            return False
    
    def start_containers(self) -> bool:
        """Запуск контейнеров"""
        try:
            print("🚀 Запуск Docker контейнеров...")
            
            response = input("❓ Запустить контейнеры сейчас? (y/n): ").lower().strip()
            if response != 'y':
                print("ℹ️ Запуск контейнеров пропущен")
                print("🔧 Для запуска выполните: docker compose up -d")
                self.log_step("Запуск контейнеров пропущен", True)
                return True
            
            print("📦 Собираем образы...")
            result = subprocess.run(
                self.compose_command + ["build"],
                cwd=self.project_root,
                timeout=300  # 5 минут на сборку
            )
            
            if result.returncode != 0:
                print("❌ Ошибка сборки образов")
                return False
            
            print("🚀 Запускаем контейнеры...")
            result = subprocess.run(
                self.compose_command + ["up", "-d"],
                cwd=self.project_root,
                timeout=120  # 2 минуты на запуск
            )
            
            if result.returncode != 0:
                print("❌ Ошибка запуска контейнеров")
                return False
            
            print("✅ Контейнеры запущены")
            print("\n📋 Полезные команды:")
            print("   🔍 Статус: docker compose ps")
            print("   📜 Логи: docker compose logs -f")
            print("   🛑 Остановка: docker compose down")
            print("   🌐 API: http://localhost:8000/docs")
            
            self.log_step("Контейнеры запущены", True)
            return True
            
        except subprocess.TimeoutExpired:
            print("❌ Таймаут при запуске контейнеров")
            return False
        except Exception as e:
            self.log_step("Ошибка запуска контейнеров", False)
            print(f"   Детали: {e}")
            return False
    
    def run_comprehensive_setup(self) -> bool:
        """Запуск полной настройки Docker"""
        print("🐳 Настройка Docker окружения для Avito AI Bot")
        print("=" * 60)
        
        steps = [
            ("Проверка Docker", self.check_docker_installation),
            ("Создание директорий", self.create_directories),
            ("Генерация секретных ключей", self.generate_secrets),
            ("Создание .env файла", self.create_env_file),
            ("Исправление alembic.ini", self.fix_alembic_ini),
            ("Создание конфигурации Nginx", self.create_nginx_config),
            ("Тестирование конфигурации", self.test_docker_setup),
            ("Запуск контейнеров", self.start_containers),
        ]
        
        for step_name, step_func in steps:
            print(f"\n🔄 {step_name}...")
            try:
                if not step_func():
                    print(f"\n❌ Настройка остановлена на шаге: {step_name}")
                    self._print_summary(False)
                    return False
            except Exception as e:
                print(f"❌ Критическая ошибка в шаге '{step_name}': {e}")
                self._print_summary(False)
                return False
        
        self._print_summary(True)
        return True
    
    def _print_summary(self, success: bool):
        """Вывод итогового отчета"""
        print("\n" + "=" * 60)
        
        if success:
            print("🎉 НАСТРОЙКА DOCKER ЗАВЕРШЕНА УСПЕШНО!")
        else:
            print("❌ НАСТРОЙКА DOCKER ЗАВЕРШЕНА С ОШИБКАМИ")
        
        print(f"📊 Статистика:")
        print(f"   ✅ Шагов завершено: {self.execution_stats['steps_completed']}/{self.execution_stats['total_steps']}")
        
        if self.execution_stats['warnings']:
            print(f"   ⚠️ Предупреждений: {len(self.execution_stats['warnings'])}")
        
        if self.execution_stats['errors']:
            print(f"   ❌ Ошибок: {len(self.execution_stats['errors'])}")
        
        if success:
            print(f"\n📋 Что создано:")
            print(f"   🐳 Dockerfile")
            print(f"   🐙 docker-compose.yml")
            print(f"   🔐 secrets/ (секретные ключи)")
            print(f"   📄 .env (переменные окружения)")
            print(f"   🌐 docker/nginx/ (конфигурации)")
            
            print(f"\n🚀 Следующие шаги:")
            print(f"   1. Замените API ключи в файле .env")
            print(f"   2. Замените заглушки в папке secrets/")
            print(f"   3. Проверьте контейнеры: docker compose ps")
            print(f"   4. Откройте API: http://localhost:8000/docs")


def main():
    """Главная функция"""
    try:
        setup = DockerSetup()
        success = setup.run_comprehensive_setup()
        
        if success:
            print("\n✅ Скрипт выполнен успешно")
            sys.exit(0)
        else:
            print("\n❌ Скрипт завершился с ошибками")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Настройка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()