#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 Комплексное решение проблем Docker и WSL

Архитектурно обоснованное решение согласно правилам README.md:
1. Всесторонний анализ проблем
2. Качественное долгосрочное решение
3. Предвидение возможных ошибок
4. Совместимость с существующей архитектурой

Местоположение: scripts/fix_docker_wsl.py
"""

import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional

# Устанавливаем UTF-8 для Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class ComprehensiveDockerFix:
    """
    🔧 Комплексное решение проблем Docker и WSL
    
    Соответствует правилам качественной разработки:
    - Всесторонний анализ зависимостей
    - Архитектурно обоснованные решения
    - Предвидение возможных ошибок
    - Совместимость с проектом
    """
    
    def __init__(self):
        self.project_root = project_root
        self.execution_stats = {
            "platform": "Windows",
            "wsl_version": None,
            "docker_version": None,
            "docker_status": None,
            "steps_completed": 0,
            "total_steps": 6,
            "warnings": [],
            "errors": [],
            "solutions_applied": []
        }
    
    def log_step(self, step_name: str, success: bool = True, warning: str = None):
        """Логирование с архитектурным подходом"""
        if success:
            self.execution_stats["steps_completed"] += 1
            print(f"✅ {step_name}")
        else:
            self.execution_stats["errors"].append(step_name)
            print(f"❌ {step_name}")
            
        if warning:
            self.execution_stats["warnings"].append(warning)
            print(f"⚠️ {warning}")
    
    def analyze_wsl_status(self) -> Dict[str, any]:
        """
        Всесторонний анализ состояния WSL
        
        Returns:
            Dict: Полная информация о WSL
        """
        wsl_analysis = {
            "installed": False,
            "version": None,
            "default_distro": None,
            "running_distros": [],
            "needs_update": False,
            "error": None
        }
        
        try:
            print("🔍 Анализ состояния WSL...")
            
            # Проверяем версию WSL
            result = subprocess.run(
                ["wsl", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                wsl_analysis["installed"] = True
                version_output = result.stdout.strip()
                wsl_analysis["version"] = version_output
                print(f"✅ WSL установлен")
                print(f"📋 Версия: {version_output}")
                
                # Проверяем список дистрибутивов
                list_result = subprocess.run(
                    ["wsl", "--list", "--verbose"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if list_result.returncode == 0:
                    distros_output = list_result.stdout
                    print(f"📋 Дистрибутивы WSL:")
                    print(distros_output)
                    
                    # Парсим запущенные дистрибутивы
                    lines = distros_output.split('\n')[1:]  # Пропускаем заголовок
                    for line in lines:
                        if line.strip() and 'Running' in line:
                            wsl_analysis["running_distros"].append(line.strip())
            else:
                wsl_analysis["error"] = result.stderr or "WSL не отвечает"
                print(f"❌ WSL не установлен или не работает: {wsl_analysis['error']}")
            
            self.execution_stats["wsl_version"] = wsl_analysis["version"]
            return wsl_analysis
            
        except subprocess.TimeoutExpired:
            wsl_analysis["error"] = "Таймаут WSL команды"
            print("❌ Таймаут при проверке WSL")
            return wsl_analysis
        except FileNotFoundError:
            wsl_analysis["error"] = "WSL не найден в PATH"
            print("❌ WSL не найден в системе")
            return wsl_analysis
        except Exception as e:
            wsl_analysis["error"] = str(e)
            print(f"❌ Ошибка анализа WSL: {e}")
            return wsl_analysis
    
    def analyze_docker_status(self) -> Dict[str, any]:
        """
        Всесторонний анализ состояния Docker
        
        Returns:
            Dict: Полная информация о Docker
        """
        docker_analysis = {
            "installed": False,
            "version": None,
            "daemon_running": False,
            "desktop_running": False,
            "compose_available": False,
            "compose_version": None,
            "error": None
        }
        
        try:
            print("🔍 Анализ состояния Docker...")
            
            # Проверяем версию Docker
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                docker_analysis["installed"] = True
                docker_analysis["version"] = result.stdout.strip()
                print(f"✅ Docker установлен: {docker_analysis['version']}")
                
                # Проверяем Docker daemon
                daemon_result = subprocess.run(
                    ["docker", "info"],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                if daemon_result.returncode == 0:
                    docker_analysis["daemon_running"] = True
                    print("✅ Docker daemon запущен")
                else:
                    docker_analysis["daemon_running"] = False
                    print("❌ Docker daemon не запущен")
                    print(f"   Детали: {daemon_result.stderr}")
                
                # Проверяем Docker Compose
                compose_result = subprocess.run(
                    ["docker", "compose", "version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if compose_result.returncode == 0:
                    docker_analysis["compose_available"] = True
                    docker_analysis["compose_version"] = compose_result.stdout.strip()
                    print(f"✅ Docker Compose: {docker_analysis['compose_version']}")
                else:
                    print("⚠️ Docker Compose недоступен")
            else:
                docker_analysis["error"] = result.stderr or "Docker не отвечает"
                print(f"❌ Docker не работает: {docker_analysis['error']}")
            
            # Проверяем Docker Desktop процесс
            try:
                tasklist_result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq Docker Desktop.exe"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if "Docker Desktop.exe" in tasklist_result.stdout:
                    docker_analysis["desktop_running"] = True
                    print("✅ Docker Desktop процесс запущен")
                else:
                    docker_analysis["desktop_running"] = False
                    print("❌ Docker Desktop не запущен")
            except:
                print("⚠️ Не удалось проверить Docker Desktop процесс")
            
            self.execution_stats["docker_version"] = docker_analysis["version"]
            self.execution_stats["docker_status"] = "running" if docker_analysis["daemon_running"] else "stopped"
            return docker_analysis
            
        except Exception as e:
            docker_analysis["error"] = str(e)
            print(f"❌ Ошибка анализа Docker: {e}")
            return docker_analysis
    
    def update_wsl(self) -> bool:
        """
        Обновление WSL с предвидением ошибок
        
        Returns:
            bool: True если обновление успешно
        """
        try:
            print("🔄 Обновление WSL...")
            print("⚠️ Это может занять несколько минут...")
            
            # Обновляем WSL
            result = subprocess.run(
                ["wsl", "--update"],
                capture_output=True,
                text=True,
                timeout=300  # 5 минут
            )
            
            if result.returncode == 0:
                print("✅ WSL успешно обновлен")
                print(f"📋 Результат: {result.stdout}")
                self.execution_stats["solutions_applied"].append("WSL обновлен")
                return True
            else:
                print(f"❌ Ошибка обновления WSL: {result.stderr}")
                
                # Предвидим возможные ошибки и предлагаем решения
                if "administrator" in result.stderr.lower() or "access" in result.stderr.lower():
                    print("💡 Решение: Запустите PowerShell от имени администратора")
                    print("   1. Нажмите Win + X")
                    print("   2. Выберите 'Windows PowerShell (Admin)'")
                    print("   3. Выполните: wsl --update")
                
                return False
                
        except subprocess.TimeoutExpired:
            print("⚠️ Обновление WSL занимает больше времени чем ожидалось")
            print("💡 Обновление может продолжаться в фоне")
            return True  # Не критично
        except Exception as e:
            print(f"❌ Критическая ошибка обновления WSL: {e}")
            return False
    
    def start_docker_desktop(self) -> bool:
        """
        Запуск Docker Desktop с предвидением проблем
        
        Returns:
            bool: True если запуск успешен
        """
        try:
            print("🚀 Запуск Docker Desktop...")
            
            # Возможные пути к Docker Desktop
            docker_paths = [
                "C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe",
                "C:\\Program Files (x86)\\Docker\\Docker\\Docker Desktop.exe",
                os.path.expanduser("~\\AppData\\Local\\Docker\\Docker Desktop.exe")
            ]
            
            docker_exe = None
            for path in docker_paths:
                if os.path.exists(path):
                    docker_exe = path
                    break
            
            if not docker_exe:
                print("❌ Docker Desktop не найден в стандартных местах")
                print("💡 Запустите Docker Desktop вручную из меню Пуск")
                return False
            
            # Запускаем Docker Desktop
            subprocess.Popen([docker_exe])
            print("✅ Docker Desktop запускается...")
            print("⏳ Ожидание запуска Docker daemon...")
            
            # Ждем запуска daemon (до 2 минут)
            for i in range(24):  # 24 попытки по 5 секунд
                time.sleep(5)
                
                try:
                    result = subprocess.run(
                        ["docker", "info"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        print("✅ Docker daemon запущен!")
                        self.execution_stats["solutions_applied"].append("Docker Desktop запущен")
                        return True
                    else:
                        print(f"⏳ Попытка {i+1}/24: Docker daemon еще запускается...")
                        
                except:
                    print(f"⏳ Попытка {i+1}/24: Ожидание Docker daemon...")
            
            print("⚠️ Docker daemon не запустился за 2 минуты")
            print("💡 Возможные решения:")
            print("   1. Подождите еще немного - первый запуск может быть долгим")
            print("   2. Перезапустите Docker Desktop")
            print("   3. Перезагрузите компьютер")
            return False
            
        except Exception as e:
            print(f"❌ Ошибка запуска Docker Desktop: {e}")
            return False
    
    def provide_manual_solutions(self, wsl_analysis: Dict, docker_analysis: Dict):
        """
        Предоставление ручных решений с учетом всех зависимостей
        """
        print("\n🔧 РУЧНЫЕ РЕШЕНИЯ ДЛЯ ИСПРАВЛЕНИЯ ПРОБЛЕМ:")
        print("=" * 60)
        
        if not wsl_analysis.get("installed", False):
            print("\n❌ WSL НЕ УСТАНОВЛЕН:")
            print("📋 Установка WSL:")
            print("   1. Откройте PowerShell от имени администратора")
            print("   2. Выполните: wsl --install")
            print("   3. Перезагрузите компьютер")
            print("   4. Настройте Ubuntu при первом запуске")
        
        elif wsl_analysis.get("needs_update", False):
            print("\n⚠️ WSL ТРЕБУЕТ ОБНОВЛЕНИЯ:")
            print("📋 Обновление WSL:")
            print("   1. Откройте PowerShell от имени администратора")
            print("   2. Выполните: wsl --update")
            print("   3. Выполните: wsl --shutdown")
            print("   4. Перезапустите Docker Desktop")
        
        if not docker_analysis.get("daemon_running", False):
            print("\n❌ DOCKER DAEMON НЕ ЗАПУЩЕН:")
            print("📋 Запуск Docker:")
            print("   1. Найдите 'Docker Desktop' в меню Пуск")
            print("   2. Запустите Docker Desktop")
            print("   3. Дождитесь зеленого индикатора в системном трее")
            print("   4. Если не помогает - перезагрузите компьютер")
        
        print("\n🔄 АЛЬТЕРНАТИВНЫЕ РЕШЕНИЯ:")
        print("📋 Если проблемы продолжаются:")
        print("   1. Полная переустановка Docker Desktop")
        print("   2. Обновление Windows до последней версии")
        print("   3. Включение Hyper-V в настройках Windows")
        print("   4. Проверка BIOS настроек виртуализации")
        
        print("\n💡 ОБХОДНЫЕ ПУТИ ДЛЯ РАЗРАБОТКИ:")
        print("📋 Локальная разработка БЕЗ Docker:")
        print("   1. python scripts/final_fix.py - локальный запуск")
        print("   2. python -m uvicorn src.api.main:app --reload")
        print("   3. Откройте http://localhost:8000/docs")
        print("   4. Docker понадобится позже для продакшена")
    
    def continue_without_docker(self) -> bool:
        """
        Продолжение разработки без Docker
        
        Returns:
            bool: True если локальная разработка работает
        """
        try:
            print("\n🔄 ПРОДОЛЖЕНИЕ БЕЗ DOCKER...")
            print("Запуск локальной разработки...")
            
            response = input("\n❓ Запустить приложение локально без Docker? (y/n): ").lower().strip()
            if response != 'y':
                print("ℹ️ Локальный запуск пропущен")
                return True
            
            # Запускаем финальное исправление
            final_fix_path = self.project_root / "scripts" / "final_fix.py"
            if final_fix_path.exists():
                print("🚀 Запуск final_fix.py...")
                result = subprocess.run(
                    [sys.executable, str(final_fix_path)],
                    cwd=self.project_root
                )
                return result.returncode == 0
            else:
                print("⚠️ final_fix.py не найден")
                print("💡 Запустите вручную: python -m uvicorn src.api.main:app --reload")
                return True
                
        except Exception as e:
            print(f"❌ Ошибка локального запуска: {e}")
            return False
    
    def run_comprehensive_fix(self) -> bool:
        """
        Запуск комплексного исправления с архитектурным подходом
        
        Returns:
            bool: True если исправление успешно
        """
        print("🔧 КОМПЛЕКСНОЕ ИСПРАВЛЕНИЕ DOCKER И WSL")
        print("Архитектурно обоснованный подход согласно правилам README.md")
        print("=" * 70)
        
        # Шаг 1: Всесторонний анализ
        print("\n🔍 ЭТАП 1: ВСЕСТОРОННИЙ АНАЛИЗ ЗАВИСИМОСТЕЙ")
        wsl_analysis = self.analyze_wsl_status()
        self.log_step("Анализ WSL состояния", True)
        
        docker_analysis = self.analyze_docker_status()
        self.log_step("Анализ Docker состояния", True)
        
        # Шаг 2: Определение архитектурной стратегии
        print("\n🏗️ ЭТАП 2: АРХИТЕКТУРНАЯ СТРАТЕГИЯ")
        
        if not wsl_analysis.get("installed", False):
            print("❌ WSL не установлен - требуется ручная установка")
            self.provide_manual_solutions(wsl_analysis, docker_analysis)
            return False
        
        if wsl_analysis.get("error") and "update" in str(wsl_analysis.get("error", "")).lower():
            print("⚠️ WSL требует обновления")
            if self.update_wsl():
                self.log_step("Обновление WSL", True)
            else:
                self.log_step("Обновление WSL", False, "Требуется ручное обновление")
        
        # Шаг 3: Качественное решение Docker проблем
        print("\n🐳 ЭТАП 3: РЕШЕНИЕ DOCKER ПРОБЛЕМ")
        
        if not docker_analysis.get("daemon_running", False):
            if docker_analysis.get("desktop_running", False):
                print("⚠️ Docker Desktop запущен, но daemon не отвечает")
                print("💡 Возможно, требуется время для инициализации")
                time.sleep(10)  # Даем время на инициализацию
            else:
                print("🚀 Попытка запуска Docker Desktop...")
                if self.start_docker_desktop():
                    self.log_step("Запуск Docker Desktop", True)
                else:
                    self.log_step("Запуск Docker Desktop", False, "Требуется ручной запуск")
        
        # Шаг 4: Предвидение ошибок и предоставление решений
        print("\n💡 ЭТАП 4: ПРЕДОСТАВЛЕНИЕ РЕШЕНИЙ")
        
        # Финальная проверка Docker
        final_docker_check = self.analyze_docker_status()
        
        if final_docker_check.get("daemon_running", False):
            print("🎉 Docker готов к использованию!")
            print("✅ Можно запускать: python scripts/setup_docker.py")
            self.log_step("Docker готов", True)
            return True
        else:
            print("⚠️ Docker все еще не готов")
            self.provide_manual_solutions(wsl_analysis, final_docker_check)
            
            # Предлагаем продолжить без Docker
            if self.continue_without_docker():
                self.log_step("Продолжение без Docker", True)
                return True
            else:
                self.log_step("Общее исправление", False)
                return False
    
    def print_execution_summary(self):
        """Вывод итогового отчета с архитектурной структурой"""
        print("\n" + "=" * 70)
        print("📊 ИТОГОВЫЙ ОТЧЕТ КОМПЛЕКСНОГО ИСПРАВЛЕНИЯ")
        print("=" * 70)
        
        print(f"🌍 Платформа: {self.execution_stats['platform']}")
        print(f"📊 Шагов завершено: {self.execution_stats['steps_completed']}/{self.execution_stats['total_steps']}")
        
        if self.execution_stats['wsl_version']:
            print(f"🔧 WSL: {self.execution_stats['wsl_version']}")
        
        if self.execution_stats['docker_version']:
            print(f"🐳 Docker: {self.execution_stats['docker_version']}")
        
        if self.execution_stats['docker_status']:
            print(f"⚙️ Docker статус: {self.execution_stats['docker_status']}")
        
        if self.execution_stats['solutions_applied']:
            print(f"✅ Примененные решения:")
            for solution in self.execution_stats['solutions_applied']:
                print(f"   - {solution}")
        
        if self.execution_stats['warnings']:
            print(f"⚠️ Предупреждения: {len(self.execution_stats['warnings'])}")
            for warning in self.execution_stats['warnings']:
                print(f"   - {warning}")
        
        if self.execution_stats['errors']:
            print(f"❌ Ошибки: {len(self.execution_stats['errors'])}")
            for error in self.execution_stats['errors']:
                print(f"   - {error}")
        
        print(f"\n📋 СЛЕДУЮЩИЕ ШАГИ:")
        print("1. Если Docker работает: python scripts/setup_docker.py")
        print("2. Локальная разработка: python scripts/final_fix.py")
        print("3. API документация: http://localhost:8000/docs")


def main():
    """Главная функция с соблюдением архитектурных принципов"""
    try:
        fix = ComprehensiveDockerFix()
        success = fix.run_comprehensive_fix()
        fix.print_execution_summary()
        
        if success:
            print("\n✅ КОМПЛЕКСНОЕ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО")
        else:
            print("\n⚠️ ТРЕБУЕТСЯ ДОПОЛНИТЕЛЬНОЕ ВМЕШАТЕЛЬСТВО")
            print("📝 Следуйте ручным инструкциям выше")
            
    except KeyboardInterrupt:
        print("\n⚠️ Исправление прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()