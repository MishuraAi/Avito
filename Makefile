# 🛠️ Makefile для управления проектом Avito AI Bot

# Переменные
PYTHON := python
PIP := pip
PYTEST := pytest
ALEMBIC := alembic
UVICORN := uvicorn

# Цвета для вывода
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

.PHONY: help install install-dev setup test test-unit test-integration test-coverage clean lint format check-db init-db run docs

# По умолчанию показываем помощь
help:
	@echo "$(GREEN)🚀 Avito AI Bot - Команды управления проектом$(NC)"
	@echo ""
	@echo "$(YELLOW)📦 Установка и настройка:$(NC)"
	@echo "  install          - Установить продакшен зависимости"
	@echo "  install-dev      - Установить зависимости для разработки"
	@echo "  setup           - Полная настройка проекта"
	@echo ""
	@echo "$(YELLOW)🗄️ База данных:$(NC)"
	@echo "  check-db        - Проверить подключение к БД"
	@echo "  setup-db        - Создать БД и пользователя"
	@echo "  init-db         - Инициализировать миграции"
	@echo "  migrate         - Применить миграции"
	@echo "  migration       - Создать новую миграцию"
	@echo ""
	@echo "$(YELLOW)🧪 Тестирование:$(NC)"
	@echo "  test            - Запустить все тесты"
	@echo "  test-unit       - Запустить unit тесты"
	@echo "  test-integration- Запустить integration тесты"
	@echo "  test-coverage   - Тесты с покрытием кода"
	@echo "  test-complete   - Полное тестирование системы"
	@echo ""
	@echo "$(YELLOW)🔧 Разработка:$(NC)"
	@echo "  run             - Запустить сервер разработки"
	@echo "  run-prod        - Запустить продакшен сервер"
	@echo "  lint            - Проверить код линтерами"
	@echo "  format          - Отформатировать код"
	@echo "  clean           - Очистить временные файлы"
	@echo ""
	@echo "$(YELLOW)📚 Документация:$(NC)"
	@echo "  docs            - Открыть API документацию"

# ============================================================================
# 📦 УСТАНОВКА И НАСТРОЙКА
# ============================================================================

install:
	@echo "$(GREEN)📦 Установка продакшен зависимостей...$(NC)"
	$(PIP) install -r requirements.txt

install-dev:
	@echo "$(GREEN)📦 Установка зависимостей для разработки...$(NC)"
	$(PIP) install -r requirements-dev.txt
	@echo "$(GREEN)✅ Зависимости установлены$(NC)"

setup: install-dev
	@echo "$(GREEN)🚀 Полная настройка проекта...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)📄 Создание .env файла...$(NC)"; \
		cp .env.example .env; \
		echo "$(RED)⚠️ Отредактируйте .env файл с вашими настройками!$(NC)"; \
	fi
	@echo "$(GREEN)✅ Проект настроен. Выполните 'make setup-db' для настройки БД$(NC)"

# ============================================================================
# 🗄️ БАЗА ДАННЫХ
# ============================================================================

check-db:
	@echo "$(GREEN)🔍 Проверка подключения к базе данных...$(NC)"
	$(PYTHON) scripts/check_database.py

setup-db:
	@echo "$(GREEN)🛠️ Настройка базы данных...$(NC)"
	$(PYTHON) scripts/setup_database.py

init-db:
	@echo "$(GREEN)🔄 Инициализация миграций...$(NC)"
	$(PYTHON) scripts/init_migrations.py

migrate:
	@echo "$(GREEN)📈 Применение миграций...$(NC)"
	$(ALEMBIC) upgrade head
	@echo "$(GREEN)✅ Миграции применены$(NC)"

migration:
	@echo "$(GREEN)📝 Создание новой миграции...$(NC)"
	@read -p "Введите описание миграции: " desc; \
	$(ALEMBIC) revision --autogenerate -m "$$desc"

# ============================================================================
# 🧪 ТЕСТИРОВАНИЕ
# ============================================================================

test:
	@echo "$(GREEN)🧪 Запуск всех тестов...$(NC)"
	$(PYTEST) -v

test-unit:
	@echo "$(GREEN)🧪 Запуск unit тестов...$(NC)"
	$(PYTEST) tests/unit/ -v -m "not external"

test-integration:
	@echo "$(GREEN)🧪 Запуск integration тестов...$(NC)"
	$(PYTEST) tests/integration/ -v -m "not external"

test-coverage:
	@echo "$(GREEN)📊 Тесты с покрытием кода...$(NC)"
	$(PYTEST) --cov=src --cov-report=html --cov-report=term-missing

test-complete:
	@echo "$(GREEN)🔬 Полное тестирование системы...$(NC)"
	$(PYTHON) scripts/test_complete_setup.py

test-external:
	@echo "$(GREEN)🌐 Тесты внешних сервисов...$(NC)"
	$(PYTEST) -v -m "external"

# ============================================================================
# 🔧 РАЗРАБОТКА
# ============================================================================

run:
	@echo "$(GREEN)🚀 Запуск сервера разработки...$(NC)"
	$(UVICORN) src.api.main:app --reload --host 0.0.0.0 --port 8000

run-prod:
	@echo "$(GREEN)🚀 Запуск продакшен сервера...$(NC)"
	$(UVICORN) src.api.main:app --host 0.0.0.0 --port 8000 --workers 4

dev: run

lint:
	@echo "$(GREEN)🔍 Проверка кода линтерами...$(NC)"
	@echo "Flake8..."
	-flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503
	@echo "Black (dry-run)..."
	-black --check src/ tests/
	@echo "isort (dry-run)..."
	-isort --check-only src/ tests/

format:
	@echo "$(GREEN)🎨 Форматирование кода...$(NC)"
	black src/ tests/
	isort src/ tests/
	@echo "$(GREEN)✅ Код отформатирован$(NC)"

clean:
	@echo "$(GREEN)🧹 Очистка временных файлов...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf test.db
	@echo "$(GREEN)✅ Очистка завершена$(NC)"

# ============================================================================
# 📚 ДОКУМЕНТАЦИЯ
# ============================================================================

docs:
	@echo "$(GREEN)📚 Открытие API документации...$(NC)"
	@echo "Запуск сервера для документации..."
	@echo "Документация будет доступна по адресу:"
	@echo "  • Swagger UI: http://localhost:8000/docs"
	@echo "  • ReDoc:      http://localhost:8000/redoc"
	@echo ""
	$(UVICORN) src.api.main:app --reload --host 0.0.0.0 --port 8000

# ============================================================================
# 🏗️ DOCKER
# ============================================================================

docker-build:
	@echo "$(GREEN)🐳 Сборка Docker образа...$(NC)"
	docker build -t avito-ai-bot .

docker-run:
	@echo "$(GREEN)🐳 Запуск в Docker контейнере...$(NC)"
	docker run -p 8000:8000 --env-file .env avito-ai-bot

docker-compose:
	@echo "$(GREEN)🐳 Запуск с Docker Compose...$(NC)"
	docker-compose up -d

docker-stop:
	@echo "$(GREEN)🐳 Остановка Docker Compose...$(NC)"
	docker-compose down

# ============================================================================
# 🔄 УТИЛИТЫ
# ============================================================================

status:
	@echo "$(GREEN)📊 Статус проекта:$(NC)"
	@echo "Python: $(shell $(PYTHON) --version)"
	@echo "Pip: $(shell $(PIP) --version)"
	@echo "База данных:"
	@$(PYTHON) scripts/check_database.py 2>/dev/null || echo "  ❌ Не настроена"
	@echo "Миграции:"
	@$(ALEMBIC) current 2>/dev/null || echo "  ❌ Не инициализированы"

update-deps:
	@echo "$(GREEN)📦 Обновление зависимостей...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt --upgrade

requirements:
	@echo "$(GREEN)📝 Обновление requirements.txt...$(NC)"
	$(PIP) freeze > requirements.txt

# ============================================================================
# 🎯 БЫСТРЫЕ КОМАНДЫ
# ============================================================================

# Быстрая настройка для новых разработчиков
quick-setup: setup setup-db init-db migrate
	@echo "$(GREEN)🎉 Быстрая настройка завершена!$(NC)"
	@echo "Запустите 'make run' для старта сервера"

# Полная проверка перед коммитом
pre-commit: format lint test
	@echo "$(GREEN)✅ Код готов к коммиту$(NC)"

# Полный цикл разработки
dev-cycle: clean install-dev init-db migrate test run

# Безопасная очистка (с подтверждением)
clean-all:
	@echo "$(RED)⚠️ Это удалит ВСЕ временные файлы и БД!$(NC)"
	@read -p "Вы уверены? [y/N]: " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		make clean; \
		rm -f test.db; \
		rm -rf migrations/; \
		echo "$(GREEN)✅ Полная очистка завершена$(NC)"; \
	else \
		echo "$(YELLOW)Отменено$(NC)"; \
	fi