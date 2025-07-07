#!/usr/bin/env python3
"""
🐳 Скрипт управления Docker для Avito AI Responder
Файл: scripts/docker_manager.py

Автоматизирует управление Docker контейнерами для разработки и продакшена.
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path
from typing import List, Optional


class Colors:
    """🎨 ANSI цвета для красивого вывода"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


class DockerManager:
    """🐳 Менеджер Docker контейнеров"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.docker_dir = self.project_root / "docker"
        
    def print_banner(self):
        """🎯 Печать баннера"""
        print(f"{Colors.CYAN}{Colors.BOLD}")
        print("╔════════════════════════════════════════════════════════════╗")
        print("║                🐳 AVITO AI RESPONDER                      ║")
        print("║                 Docker Manager v1.0                       ║")
        print("╚════════════════════════════════════════════════════════════╝")
        print(f"{Colors.END}")

    def run_command(self, command: List[str], cwd: Optional[Path] = None) -> bool:
        """
        🚀 Выполнение команды с логированием
        
        Args:
            command: Команда для выполнения
            cwd: Рабочая директория
            
        Returns:
            bool: True если команда выполнена успешно
        """
        try:
            cmd_str = " ".join(command)
            print(f"{Colors.BLUE}🔄 Выполняю: {cmd_str}{Colors.END}")
            
            result = subprocess.run(
                command,
                cwd=cwd or self.project_root,
                check=True,
                capture_output=False
            )
            
            print(f"{Colors.GREEN}✅ Команда выполнена успешно{Colors.END}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}❌ Ошибка выполнения команды: {e}{Colors.END}")
            return False
        except FileNotFoundError:
            print(f"{Colors.RED}❌ Команда не найдена: {command[0]}{Colors.END}")
            return False

    def check_docker(self) -> bool:
        """🔍 Проверка доступности Docker"""
        print(f"{Colors.YELLOW}🔍 Проверяю Docker...{Colors.END}")
        
        if not self.run_command(["docker", "--version"]):
            print(f"{Colors.RED}❌ Docker не установлен или недоступен{Colors.END}")
            return False
            
        if not self.run_command(["docker-compose", "--version"]):
            print(f"{Colors.RED}❌ Docker Compose не установлен{Colors.END}")
            return False
            
        print(f"{Colors.GREEN}✅ Docker готов к работе{Colors.END}")
        return True

    def build_image(self, tag: str = "latest") -> bool:
        """
        🏗️ Сборка Docker образа
        
        Args:
            tag: Тег для образа
        """
        print(f"{Colors.CYAN}🏗️ Собираю Docker образ...{Colors.END}")
        
        return self.run_command([
            "docker", "build",
            "-f", "docker/Dockerfile",
            "-t", f"avito-ai-responder:{tag}",
            "."
        ])

    def dev_up(self, services: Optional[List[str]] = None) -> bool:
        """
        🚀 Запуск среды разработки
        
        Args:
            services: Список сервисов для запуска (None = все)
        """
        print(f"{Colors.CYAN}🚀 Запускаю среду разработки...{Colors.END}")
        
        command = [
            "docker-compose",
            "-f", "docker/docker-compose.yml",
            "up", "-d"
        ]
        
        if services:
            command.extend(services)
            
        return self.run_command(command)

    def dev_down(self) -> bool:
        """🛑 Остановка среды разработки"""
        print(f"{Colors.YELLOW}🛑 Останавливаю среду разработки...{Colors.END}")
        
        return self.run_command([
            "docker-compose",
            "-f", "docker/docker-compose.yml",
            "down"
        ])

    def prod_deploy(self) -> bool:
        """🚀 Развертывание продакшена"""
        print(f"{Colors.PURPLE}🚀 Развертываю продакшен...{Colors.END}")
        
        # Сначала собираем образ
        if not self.build_image("latest"):
            return False
            
        # Затем запускаем продакшен
        return self.run_command([
            "docker-compose",
            "-f", "docker/docker-compose.prod.yml",
            "up", "-d"
        ])

    def prod_down(self) -> bool:
        """🛑 Остановка продакшена"""
        print(f"{Colors.YELLOW}🛑 Останавливаю продакшен...{Colors.END}")
        
        return self.run_command([
            "docker-compose",
            "-f", "docker/docker-compose.prod.yml",
            "down"
        ])

    def logs(self, environment: str = "dev", service: Optional[str] = None, follow: bool = False) -> bool:
        """
        📋 Просмотр логов
        
        Args:
            environment: dev или prod
            service: Имя сервиса (None = все)
            follow: Следить за логами в реальном времени
        """
        compose_file = "docker-compose.yml" if environment == "dev" else "docker-compose.prod.yml"
        
        command = [
            "docker-compose",
            "-f", f"docker/{compose_file}",
            "logs"
        ]
        
        if follow:
            command.append("-f")
            
        if service:
            command.append(service)
            
        print(f"{Colors.BLUE}📋 Показываю логи ({environment})...{Colors.END}")
        return self.run_command(command)

    def status(self, environment: str = "dev") -> bool:
        """📊 Статус контейнеров"""
        compose_file = "docker-compose.yml" if environment == "dev" else "docker-compose.prod.yml"
        
        print(f"{Colors.BLUE}📊 Статус контейнеров ({environment}):${Colors.END}")
        return self.run_command([
            "docker-compose",
            "-f", f"docker/{compose_file}",
            "ps"
        ])

    def exec_shell(self, environment: str = "dev", service: str = "app") -> bool:
        """🖥️ Подключение к shell контейнера"""
        compose_file = "docker-compose.yml" if environment == "dev" else "docker-compose.prod.yml"
        
        print(f"{Colors.CYAN}🖥️ Подключаюсь к {service} ({environment})...{Colors.END}")
        return self.run_command([
            "docker-compose",
            "-f", f"docker/{compose_file}",
            "exec", service, "/bin/bash"
        ])

    def clean(self) -> bool:
        """🧹 Очистка неиспользуемых ресурсов"""
        print(f"{Colors.YELLOW}🧹 Очищаю неиспользуемые ресурсы...{Colors.END}")
        
        commands = [
            ["docker", "container", "prune", "-f"],
            ["docker", "image", "prune", "-f"],
            ["docker", "volume", "prune", "-f"],
            ["docker", "network", "prune", "-f"]
        ]
        
        for command in commands:
            if not self.run_command(command):
                return False
                
        return True

    def setup_environment(self) -> bool:
        """⚙️ Настройка переменных окружения"""
        print(f"{Colors.CYAN}⚙️ Настраиваю переменные окружения...{Colors.END}")
        
        env_example = self.project_root / ".env.example"
        env_file = self.project_root / ".env"
        
        if not env_file.exists() and env_example.exists():
            print(f"{Colors.YELLOW}📋 Копирую .env.example -> .env{Colors.END}")
            env_file.write_text(env_example.read_text())
            
        print(f"{Colors.GREEN}✅ Переменные окружения настроены{Colors.END}")
        print(f"{Colors.YELLOW}⚠️  Не забудьте отредактировать .env файл!{Colors.END}")
        return True

    def health_check(self, environment: str = "dev") -> bool:
        """🏥 Проверка здоровья сервисов"""
        print(f"{Colors.BLUE}🏥 Проверяю здоровье сервисов ({environment})...{Colors.END}")
        
        # Проверяем основные сервисы
        services = ["app", "postgres", "redis"]
        
        for service in services:
            print(f"{Colors.CYAN}🔍 Проверяю {service}...{Colors.END}")
            
            # Проверяем что контейнер запущен
            result = subprocess.run([
                "docker-compose",
                "-f", f"docker/docker-compose.yml" if environment == "dev" else "docker/docker-compose.prod.yml",
                "ps", "-q", service
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if not result.stdout.strip():
                print(f"{Colors.RED}❌ {service} не запущен{Colors.END}")
                return False
            else:
                print(f"{Colors.GREEN}✅ {service} работает{Colors.END}")
                
        return True


def main():
    """🎯 Главная функция"""
    parser = argparse.ArgumentParser(
        description="🐳 Docker Manager для Avito AI Responder",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Доступные команды")
    
    # Команда build
    subparsers.add_parser("build", help="🏗️ Собрать Docker образ")
    
    # Команды для разработки
    dev_parser = subparsers.add_parser("dev", help="🚀 Управление средой разработки")
    dev_subparsers = dev_parser.add_subparsers(dest="dev_action")
    dev_subparsers.add_parser("up", help="Запустить среду разработки")
    dev_subparsers.add_parser("down", help="Остановить среду разработки")
    dev_subparsers.add_parser("status", help="Статус контейнеров")
    dev_subparsers.add_parser("logs", help="Показать логи")
    
    # Команды для продакшена
    prod_parser = subparsers.add_parser("prod", help="🚀 Управление продакшеном")
    prod_subparsers = prod_parser.add_subparsers(dest="prod_action")
    prod_subparsers.add_parser("deploy", help="Развернуть продакшен")
    prod_subparsers.add_parser("down", help="Остановить продакшен")
    prod_subparsers.add_parser("status", help="Статус контейнеров")
    prod_subparsers.add_parser("logs", help="Показать логи")
    
    # Утилиты
    subparsers.add_parser("clean", help="🧹 Очистить неиспользуемые ресурсы")
    subparsers.add_parser("setup", help="⚙️ Настроить переменные окружения")
    subparsers.add_parser("health", help="🏥 Проверить здоровье сервисов")
    
    args = parser.parse_args()
    
    manager = DockerManager()
    manager.print_banner()
    
    # Проверяем Docker
    if not manager.check_docker():
        sys.exit(1)
    
    success = True
    
    try:
        if args.command == "build":
            success = manager.build_image()
            
        elif args.command == "dev":
            if args.dev_action == "up":
                success = manager.dev_up()
            elif args.dev_action == "down":
                success = manager.dev_down()
            elif args.dev_action == "status":
                success = manager.status("dev")
            elif args.dev_action == "logs":
                success = manager.logs("dev", follow=True)
            else:
                print(f"{Colors.RED}❌ Неизвестная команда для dev: {args.dev_action}{Colors.END}")
                success = False
                
        elif args.command == "prod":
            if args.prod_action == "deploy":
                success = manager.prod_deploy()
            elif args.prod_action == "down":
                success = manager.prod_down()
            elif args.prod_action == "status":
                success = manager.status("prod")
            elif args.prod_action == "logs":
                success = manager.logs("prod", follow=True)
            else:
                print(f"{Colors.RED}❌ Неизвестная команда для prod: {args.prod_action}{Colors.END}")
                success = False
                
        elif args.command == "clean":
            success = manager.clean()
            
        elif args.command == "setup":
            success = manager.setup_environment()
            
        elif args.command == "health":
            success = manager.health_check()
            
        else:
            parser.print_help()
            success = False
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  Операция прервана пользователем{Colors.END}")
        success = False
    except Exception as e:
        print(f"{Colors.RED}❌ Неожиданная ошибка: {e}{Colors.END}")
        success = False
    
    if success:
        print(f"\n{Colors.GREEN}🎉 Операция завершена успешно!{Colors.END}")
        sys.exit(0)
    else:
        print(f"\n{Colors.RED}💥 Операция завершилась с ошибкой{Colors.END}")
        sys.exit(1)


if __name__ == "__main__":
    main()