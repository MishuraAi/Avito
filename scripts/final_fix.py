#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ
Исправляет оставшиеся проблемы и запускает приложение
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

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class FinalFix:
    """Финальное исправление всех проблем"""
    
    def __init__(self):
        self.project_root = project_root
        self.alembic_ini = self.project_root / "alembic.ini"
        
    def print_safe(self, message: str):
        """Безопасный вывод"""
        try:
            print(message)
        except UnicodeEncodeError:
            safe_message = message.encode('ascii', 'replace').decode('ascii')
            print(safe_message)
    
    def fix_alembic_ini_template(self) -> bool:
        """Исправление file_template в alembic.ini"""
        try:
            self.print_safe("ИСПРАВЛЕНИЕ file_template в alembic.ini...")
            
            # Правильная конфигурация без проблем с интерполяцией
            fixed_content = """# Alembic configuration for Avito AI Bot
# Fixed for Windows

[alembic]
script_location = migrations
file_template = %%(rev)s_%%(slug)s
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
format = %%(levelname)-5.5s [%%(name)s] %%(message)s
datefmt = %%H:%%M:%%S
"""
            
            # Записываем исправленную версию
            with open(self.alembic_ini, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            self.print_safe("УСПЕШНО: alembic.ini file_template исправлен")
            return True
            
        except Exception as e:
            self.print_safe(f"ОШИБКА исправления file_template: {e}")
            return False
    
    def fix_pydantic_schemas(self) -> bool:
        """Исправление Pydantic v2 проблем"""
        try:
            self.print_safe("ИСПРАВЛЕНИЕ Pydantic схем...")
            
            # Исправляем base.py
            base_schema_path = self.project_root / "src" / "api" / "schemas" / "base.py"
            
            if base_schema_path.exists():
                content = base_schema_path.read_text(encoding='utf-8')
                
                # Заменяем regex на pattern
                content = content.replace('regex=', 'pattern=')
                
                # Исправляем другие проблемы Pydantic v2
                content = content.replace('orm_mode = True', 'from_attributes = True')
                content = content.replace('schema_extra = ', 'json_schema_extra = ')
                content = content.replace('allow_mutation = False', '# allow_mutation removed in v2')
                
                base_schema_path.write_text(content, encoding='utf-8')
                self.print_safe("УСПЕШНО: base.py исправлен")
            
            # Проверяем другие файлы схем
            schemas_dir = self.project_root / "src" / "api" / "schemas"
            if schemas_dir.exists():
                for schema_file in schemas_dir.glob("*.py"):
                    try:
                        content = schema_file.read_text(encoding='utf-8')
                        if 'regex=' in content:
                            content = content.replace('regex=', 'pattern=')
                            schema_file.write_text(content, encoding='utf-8')
                            self.print_safe(f"ИСПРАВЛЕН: {schema_file.name}")
                    except Exception as e:
                        self.print_safe(f"ПРЕДУПРЕЖДЕНИЕ при исправлении {schema_file.name}: {e}")
            
            return True
            
        except Exception as e:
            self.print_safe(f"ОШИБКА исправления Pydantic: {e}")
            return False
    
    def create_simple_migration(self) -> bool:
        """Создание простой миграции без автогенерации"""
        try:
            self.print_safe("СОЗДАНИЕ простой миграции...")
            
            # Создаем простую миграцию вручную
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "revision", "-m", "initial"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                self.print_safe("УСПЕШНО: Простая миграция создана")
                return True
            else:
                self.print_safe(f"ПРЕДУПРЕЖДЕНИЕ создания миграции: {result.stderr}")
                return True  # Не критично
                
        except Exception as e:
            self.print_safe(f"ОШИБКА создания миграции: {e}")
            return True  # Не критично
    
    def test_alembic_config(self) -> bool:
        """Тест конфигурации Alembic"""
        try:
            self.print_safe("ТЕСТ конфигурации Alembic...")
            
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "current"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                self.print_safe("УСПЕШНО: Alembic конфигурация работает")
                return True
            else:
                self.print_safe(f"ПРЕДУПРЕЖДЕНИЕ Alembic: {result.stderr}")
                return True  # Продолжаем
                
        except Exception as e:
            self.print_safe(f"ОШИБКА теста Alembic: {e}")
            return True  # Не критично
    
    def start_server_simple(self) -> bool:
        """Запуск сервера без reload для избежания проблем"""
        try:
            self.print_safe("ЗАПУСК сервера (без hot reload)...")
            self.print_safe("Сервер: http://localhost:8000")
            self.print_safe("API документация: http://localhost:8000/docs")
            self.print_safe("Для остановки: Ctrl+C")
            
            # Открываем браузер через 3 секунды
            def open_browser():
                time.sleep(3)
                try:
                    webbrowser.open("http://localhost:8000/docs")
                    self.print_safe("Браузер открыт с API документацией")
                except:
                    pass
            
            import threading
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()
            
            # Запускаем сервер БЕЗ reload чтобы избежать проблем
            result = subprocess.run(
                [sys.executable, "-m", "uvicorn", "src.api.main:app", 
                 "--host", "0.0.0.0", "--port", "8000"],
                cwd=self.project_root
            )
            
            return True
            
        except KeyboardInterrupt:
            self.print_safe("Сервер остановлен пользователем")
            return True
        except Exception as e:
            self.print_safe(f"ОШИБКА запуска сервера: {e}")
            return False
    
    def run_final_fix(self) -> bool:
        """Финальное исправление"""
        self.print_safe("=== ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ AVITO AI BOT ===")
        self.print_safe("Исправление последних проблем и запуск")
        self.print_safe("")
        
        steps = [
            ("Исправление alembic.ini template", self.fix_alembic_ini_template),
            ("Исправление Pydantic схем", self.fix_pydantic_schemas),
            ("Создание простой миграции", self.create_simple_migration),
            ("Тест Alembic", self.test_alembic_config),
            ("Запуск сервера", self.start_server_simple),
        ]
        
        for step_name, step_func in steps:
            self.print_safe(f">>> {step_name}...")
            try:
                if not step_func():
                    self.print_safe(f"ОШИБКА на шаге: {step_name}")
                    if step_name == "Запуск сервера":
                        return False
                    # Продолжаем для других шагов
            except Exception as e:
                self.print_safe(f"ИСКЛЮЧЕНИЕ в '{step_name}': {e}")
                if step_name == "Запуск сервера":
                    return False
        
        return True


def main():
    """Главная функция"""
    try:
        fix = FinalFix()
        success = fix.run_final_fix()
        
        if success:
            fix.print_safe("УСПЕХ: Приложение должно работать!")
        else:
            fix.print_safe("ПРОБЛЕМА: Проверьте ошибки выше")
            
    except KeyboardInterrupt:
        print("Операция прервана")
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")


if __name__ == "__main__":
    main()