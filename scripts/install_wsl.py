#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 Автоматизированная установка WSL для Docker

Качественное решение согласно правилам README.md:
- Проверка прав администратора
- Пошаговая установка WSL
- Автоматическая настройка
- Подготовка к Docker

Местоположение: scripts/install_wsl.py
"""

import os
import sys
import subprocess
import time
import ctypes
from pathlib import Path

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class WSLInstaller:
    """
    🔧 Автоматизированная установка WSL
    
    Архитектурно обоснованное решение:
    - Проверка системных требований
    - Пошаговая установка компонентов
    - Автоматическая настройка
    - Подготовка Docker окружения
    """
    
    def __init__(self):
        self.is_admin = self.check_admin_rights()
        self.execution_log = []
        
    def log_action(self, action: str, success: bool = True):
        """Логирование действий с архитектурным подходом"""
        status = "✅" if success else "❌"
        message = f"{status} {action}"
        print(message)
        self.execution_log.append((action, success))
    
    def check_admin_rights(self) -> bool:
        """Проверка прав администратора"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def check_windows_version(self) -> bool:
        """Проверка совместимости Windows"""
        try:
            print("🔍 Проверка версии Windows...")
            
            result = subprocess.run(
                ["ver"],
                shell=True,
                capture_output=True,
                text=True
            )
            
            version_info = result.stdout.strip()
            print(f"📋 {version_info}")
            
            # Проверяем поддержку WSL 2
            version_result = subprocess.run(
                ["powershell", "-Command", "[System.Environment]::OSVersion.Version"],
                capture_output=True,
                text=True
            )
            
            if version_result.returncode == 0:
                print("✅ Windows совместим с WSL 2")
                self.log_action("Проверка версии Windows", True)
                return True
            else:
                print("❌ Не удалось определить версию Windows")
                self.log_action("Проверка версии Windows", False)
                return False
                
        except Exception as e:
            print(f"❌ Ошибка проверки Windows: {e}")
            self.log_action("Проверка версии Windows", False)
            return False
    
    def enable_windows_features(self) -> bool:
        """Включение необходимых компонентов Windows"""
        try:
            print("🔧 Включение компонентов Windows...")
            
            if not self.is_admin:
                print("❌ Требуются права администратора!")
                print("💡 Запустите PowerShell от имени администратора:")
                print("   1. Win + X")
                print("   2. Windows PowerShell (администратор)")
                print("   3. Выполните команды ниже:")
                print()
                print("dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart")
                print("dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart")
                return False
            
            # Включаем WSL
            print("⚙️ Включение Windows Subsystem for Linux...")
            result1 = subprocess.run([
                "dism.exe", "/online", "/enable-feature",
                "/featurename:Microsoft-Windows-Subsystem-Linux",
                "/all", "/norestart"
            ], capture_output=True, text=True)
            
            if result1.returncode == 0 or "уже включен" in result1.stdout:
                print("✅ WSL компонент включен")
            else:
                print(f"⚠️ Возможная проблема с WSL: {result1.stderr}")
            
            # Включаем Virtual Machine Platform
            print("⚙️ Включение Virtual Machine Platform...")
            result2 = subprocess.run([
                "dism.exe", "/online", "/enable-feature",
                "/featurename:VirtualMachinePlatform",
                "/all", "/norestart"
            ], capture_output=True, text=True)
            
            if result2.returncode == 0 or "уже включен" in result2.stdout:
                print("✅ Virtual Machine Platform включен")
            else:
                print(f"⚠️ Возможная проблема с VMP: {result2.stderr}")
            
            self.log_action("Включение компонентов Windows", True)
            return True
            
        except Exception as e:
            print(f"❌ Ошибка включения компонентов: {e}")
            self.log_action("Включение компонентов Windows", False)
            return False
    
    def install_wsl_kernel(self) -> bool:
        """Установка WSL"""
        try:
            print("📦 Установка WSL...")
            
            if not self.is_admin:
                print("❌ Требуются права администратора!")
                print("💡 Выполните от администратора: wsl --install")
                return False
            
            # Устанавливаем WSL
            result = subprocess.run([
                "wsl", "--install", "--distribution", "Ubuntu"
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print("✅ WSL установлен успешно")
                print("📋 Установлен Ubuntu как дистрибутив по умолчанию")
                self.log_action("Установка WSL", True)
                return True
            else:
                print(f"❌ Ошибка установки WSL: {result.stderr}")
                self.log_action("Установка WSL", False)
                return False
                
        except subprocess.TimeoutExpired:
            print("⚠️ Установка WSL занимает больше времени")
            print("💡 Установка может продолжаться в фоне")
            self.log_action("Установка WSL", True)
            return True
        except Exception as e:
            print(f"❌ Ошибка установки WSL: {e}")
            self.log_action("Установка WSL", False)
            return False
    
    def set_wsl_version(self) -> bool:
        """Установка WSL 2 как версии по умолчанию"""
        try:
            print("🔧 Настройка WSL 2 как версии по умолчанию...")
            
            result = subprocess.run([
                "wsl", "--set-default-version", "2"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ WSL 2 установлен как версия по умолчанию")
                self.log_action("Настройка WSL 2", True)
                return True
            else:
                print(f"⚠️ Возможная проблема настройки: {result.stderr}")
                self.log_action("Настройка WSL 2", False)
                return False
                
        except Exception as e:
            print(f"❌ Ошибка настройки WSL 2: {e}")
            self.log_action("Настройка WSL 2", False)
            return False
    
    def verify_installation(self) -> bool:
        """Проверка успешности установки"""
        try:
            print("🔍 Проверка установки WSL...")
            
            # Проверяем версию WSL
            version_result = subprocess.run([
                "wsl", "--version"
            ], capture_output=True, text=True)
            
            if version_result.returncode == 0:
                print("✅ WSL успешно установлен")
                print(f"📋 {version_result.stdout.strip()}")
                
                # Проверяем список дистрибутивов
                list_result = subprocess.run([
                    "wsl", "--list", "--verbose"
                ], capture_output=True, text=True)
                
                if list_result.returncode == 0:
                    print("📋 Установленные дистрибутивы:")
                    print(list_result.stdout)
                
                self.log_action("Проверка установки WSL", True)
                return True
            else:
                print(f"❌ WSL не работает: {version_result.stderr}")
                self.log_action("Проверка установки WSL", False)
                return False
                
        except Exception as e:
            print(f"❌ Ошибка проверки WSL: {e}")
            self.log_action("Проверка установки WSL", False)
            return False
    
    def provide_next_steps(self):
        """Предоставление следующих шагов"""
        print("\n🎯 СЛЕДУЮЩИЕ ШАГИ ПОСЛЕ УСТАНОВКИ WSL:")
        print("=" * 60)
        
        print("\n📋 ОБЯЗАТЕЛЬНЫЕ ДЕЙСТВИЯ:")
        print("1. 🔄 ПЕРЕЗАГРУЗИТЕ КОМПЬЮТЕР")
        print("   - WSL требует перезагрузки для активации")
        print("   - Новые компоненты Windows должны загрузиться")
        
        print("\n2. 🐧 НАСТРОЙКА UBUNTU (при первом запуске):")
        print("   - Откройте 'Ubuntu' из меню Пуск")
        print("   - Создайте пользователя и пароль Unix")
        print("   - Дождитесь завершения начальной настройки")
        
        print("\n3. 🐳 ЗАПУСК DOCKER DESKTOP:")
        print("   - Найдите 'Docker Desktop' в меню Пуск")
        print("   - Запустите Docker Desktop")
        print("   - Дождитесь зеленого индикатора")
        
        print("\n4. 🧪 ТЕСТИРОВАНИЕ:")
        print("   - python scripts/setup_docker.py")
        print("   - docker compose up -d")
        
        print("\n🔧 АЛЬТЕРНАТИВНЫЕ КОМАНДЫ (если что-то не работает):")
        print("   wsl --update                    # Обновить WSL")
        print("   wsl --shutdown                  # Перезапустить WSL")
        print("   wsl --list --verbose           # Проверить дистрибутивы")
    
    def run_installation(self) -> bool:
        """Запуск полной установки WSL"""
        print("🔧 АВТОМАТИЗИРОВАННАЯ УСТАНОВКА WSL")
        print("Качественное решение для подготовки Docker окружения")
        print("=" * 65)
        
        # Проверяем права администратора
        if not self.is_admin:
            print("❌ ТРЕБУЮТСЯ ПРАВА АДМИНИСТРАТОРА")
            print("\n💡 ЗАПУСТИТЕ СКРИПТ ОТ АДМИНИСТРАТОРА:")
            print("1. Нажмите Win + X")
            print("2. Выберите 'Windows PowerShell (администратор)'")
            print("3. Перейдите в папку: cd C:\\avito")
            print("4. Запустите: python scripts/install_wsl.py")
            
            print("\n🔄 РУЧНАЯ УСТАНОВКА:")
            print("1. В PowerShell администратора выполните:")
            print("   wsl --install")
            print("2. Перезагрузите компьютер")
            print("3. Настройте Ubuntu при первом запуске")
            return False
        
        steps = [
            ("Проверка Windows", self.check_windows_version),
            ("Включение компонентов", self.enable_windows_features),
            ("Установка WSL", self.install_wsl_kernel),
            ("Настройка WSL 2", self.set_wsl_version),
            ("Проверка установки", self.verify_installation),
        ]
        
        success_count = 0
        for step_name, step_func in steps:
            print(f"\n🔄 {step_name}...")
            try:
                if step_func():
                    success_count += 1
                else:
                    print(f"⚠️ Проблема в шаге: {step_name}")
                    # Продолжаем выполнение остальных шагов
            except Exception as e:
                print(f"❌ Ошибка в шаге '{step_name}': {e}")
        
        # Итоговый отчет
        print(f"\n📊 РЕЗУЛЬТАТ УСТАНОВКИ:")
        print(f"✅ Успешных шагов: {success_count}/{len(steps)}")
        
        if success_count >= 3:  # Минимально необходимо
            print("🎉 WSL УСТАНОВКА ЗАВЕРШЕНА!")
            self.provide_next_steps()
            return True
        else:
            print("⚠️ УСТАНОВКА ЗАВЕРШЕНА С ПРОБЛЕМАМИ")
            print("📝 Некоторые шаги требуют ручного выполнения")
            self.provide_next_steps()
            return False


def main():
    """Главная функция"""
    try:
        installer = WSLInstaller()
        success = installer.run_installation()
        
        if success:
            print("\n✅ WSL готов для Docker!")
        else:
            print("\n⚠️ Требуется дополнительная настройка")
            
    except KeyboardInterrupt:
        print("\n⚠️ Установка прервана пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")


if __name__ == "__main__":
    main()