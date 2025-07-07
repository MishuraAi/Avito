# 🛠️ Makefile для Avito AI Responder
# Автоматизация команд разработки и развертывания

.PHONY: help install test clean lint format type-check run dev prod docker-* setup

# Цвета для красивого вывода
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
PURPLE := \033[35m
CYAN := \033[36m
WHITE := \033[37m
RED := \033[31m
RESET := \033[0m

# Переменные
PYTHON := python3
PIP := pip3
DOCKER := docker
DOCKER_COMPOSE := docker-compose
PROJECT_NAME := avito-ai-responder

##@ Основные команды

help: ## 📋 Показать справку по командам
	@echo "$(CYAN)🤖 Avito AI Responder - Makefile команды$(RESET)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Использование:\n  make $(CYAN)<target>$(RESET)\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(RESET)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ 🔧 Настройка окружения

setup: ## ⚙️ Полная настройка проекта
	@echo "$(BLUE)🔧 Настройка проекта Avito AI Responder...$(RESET)"
	@$(PYTHON) -m venv venv || echo "$(YELLOW)⚠️ Виртуальное окружение уже существует$(RESET)"
	@echo "$(GREEN)✅ Активируйте виртуальное окружение: source venv/bin/activate$(RESET)"
	@echo "$(GREEN)✅ Затем выполните: make install$(RESET)"

install: ## 📦 Установка зависимостей
	@echo "$(BLUE)📦 Установка зависимостей...$(RESET)"
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements-dev.txt
	@echo "$(GREEN)✅ Зависимости установлены$(RESET)"

env: ## 📄 Копирование .env.example в .env
	@echo "$(BLUE)📄 Настройка переменных окружения...$(RESET)"
	@cp .env.example .env || echo "$(YELLOW)⚠️ .env уже существует$(RESET)"
	@echo "$(GREEN)✅ Файл .env создан. Не забудьте добавить API ключи!$(RESET)"

##@ 🗄️ База данных

db-init: ## 🔄 Инициализация миграций базы данных
	@echo "$(BLUE)🔄 Инициализация миграций...$(RESET)"
	@$(PYTHON) scripts/init_migrations.py

db-migrate: ## ⬆️ Применение миграций
	@echo "$(BLUE)⬆️ Применение миграций...$(RESET)"
	@alembic upgrade head

db-revision: ## 📝 Создание новой миграции
	@echo "$(BLUE)📝 Создание новой миграции...$(RESET)"
	@read -p "Название миграции: " name; alembic revision --autogenerate -m "$$name"

db-check: ## 🔍 Проверка состояния базы данных
	@echo "$(BLUE)🔍 Проверка базы данных...$(RESET)"
	@$(PYTHON) scripts/check_database.py

db-setup: ## 🛠️ Создание базы данных PostgreSQL
	@echo "$(BLUE)🛠️ Настройка базы данных...$(RESET)"
	@$(PYTHON) scripts/setup_database.py

##@ 🧪 Тестирование

test: ## 🧪 Запуск всех тестов
	@echo "$(BLUE)🧪 Запуск тестов...$(RESET)"
	@pytest -v

test-unit: ## 📊 Запуск unit тестов
	@echo "$(BLUE)📊 Запуск unit тестов...$(RESET)"
	@pytest tests/unit/ -v

test-integration: ## 🔗 Запуск integration тестов
	@echo "$(BLUE)🔗 Запуск integration тестов...$(RESET)"
	@pytest tests/integration/ -v

test-coverage: ## 📈 Тесты с покрытием кода
	@echo "$(BLUE)📈 Анализ покрытия кода...$(RESET)"
	@pytest --cov=src --cov-report=html --cov-report=term

test-complete: ## 🎯 Полное тестирование системы
	@echo "$(BLUE)🎯 Полное тестирование системы...$(RESET)"
	@$(PYTHON) scripts/test_complete_setup.py

##@ 🔍 Качество кода

lint: ## 🔍 Проверка кода с flake8
	@echo "$(BLUE)🔍 Проверка стиля кода...$(RESET)"
	@flake8 src/ tests/ scripts/ --max-line-length=100 --exclude=migrations/

format: ## ✨ Форматирование кода с black
	@echo "$(BLUE)✨ Форматирование кода...$(RESET)"
	@black src/ tests/ scripts/ --line-length=100 --exclude=migrations/

format-check: ## 🎯 Проверка форматирования без изменений
	@echo "$(BLUE)🎯 Проверка форматирования...$(RESET)"
	@black src/ tests/ scripts/ --check --diff --line-length=100 --exclude=migrations/

type-check: ## 🔍 Проверка типов с mypy
	@echo "$(BLUE)🔍 Проверка типов...$(RESET)"
	@mypy src/ --ignore-missing-imports

isort: ## 📋 Сортировка импортов
	@echo "$(BLUE)📋 Сортировка импортов...$(RESET)"
	@isort src/ tests/ scripts/ --profile black

isort-check: ## 🎯 Проверка сортировки импортов
	@echo "$(BLUE)🎯 Проверка импортов...$(RESET)"
	@isort src/ tests/ scripts/ --profile black --check-only --diff

code-quality: lint format type-check isort ## 🏆 Полная проверка качества кода

##@ 🚀 Запуск приложения

run: ## 🚀 Запуск сервера разработки
	@echo "$(BLUE)🚀 Запуск сервера разработки...$(RESET)"
	@uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

run-prod: ## 🚀 Запуск продакшен сервера
	@echo "$(BLUE)🚀 Запуск продакшен сервера...$(RESET)"
	@gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

##@ 🐳 Docker команды

docker-setup: ## ⚙️ Настройка Docker окружения
	@echo "$(PURPLE)🐳 Настройка Docker окружения...$(RESET)"
	@$(PYTHON) scripts/docker_manager.py setup

docker-build: ## 🏗️ Сборка Docker образа
	@echo "$(PURPLE)🏗️ Сборка Docker образа...$(RESET)"
	@$(PYTHON) scripts/docker_manager.py build

docker-dev-up: ## 🚀 Запуск среды разработки в Docker
	@echo "$(PURPLE)🚀 Запуск среды разработки...$(RESET)"
	@$(PYTHON) scripts/docker_manager.py dev up

docker-dev-down: ## 🛑 Остановка среды разработки
	@echo "$(PURPLE)🛑 Остановка среды разработки...$(RESET)"
	@$(PYTHON) scripts/docker_manager.py dev down

docker-dev-logs: ## 📋 Просмотр логов разработки
	@echo "$(PURPLE)📋 Просмотр логов...$(RESET)"
	@$(PYTHON) scripts/docker_manager.py dev logs

docker-dev-status: ## 📊 Статус контейнеров разработки
	@echo "$(PURPLE)📊 Статус контейнеров...$(RESET)"
	@$(PYTHON) scripts/docker_manager.py dev status

docker-prod-deploy: ## 🚀 Развертывание продакшена
	@echo "$(PURPLE)🚀 Развертывание продакшена...$(RESET)"
	@$(PYTHON) scripts/docker_manager.py prod deploy

docker-prod-down: ## 🛑 Остановка продакшена
	@echo "$(PURPLE)🛑 Остановка продакшена...$(RESET)"
	@$(PYTHON) scripts/docker_manager.py prod down

docker-health: ## 🏥 Проверка здоровья сервисов
	@echo "$(PURPLE)🏥 Проверка здоровья сервисов...$(RESET)"
	@$(PYTHON) scripts/docker_manager.py health

docker-clean: ## 🧹 Очистка Docker ресурсов
	@echo "$(PURPLE)🧹 Очистка Docker ресурсов...$(RESET)"
	@$(PYTHON) scripts/docker_manager.py clean

##@ 🐳 Прямые Docker команды

docker-build-direct: ## 🏗️ Прямая сборка образа
	@echo "$(CYAN)🏗️ Прямая сборка Docker образа...$(RESET)"
	@$(DOCKER) build -f docker/Dockerfile -t $(PROJECT_NAME):latest .

docker-run-direct: ## 🚀 Прямой запуск контейнера
	@echo "$(CYAN)🚀 Прямой запуск контейнера...$(RESET)"
	@$(DOCKER) run -d --name $(PROJECT_NAME)-test -p 8000:8000 $(PROJECT_NAME):latest

docker-compose-dev: ## 🔧 Docker Compose для разработки
	@echo "$(CYAN)🔧 Запуск Docker Compose (разработка)...$(RESET)"
	@$(DOCKER_COMPOSE) -f docker/docker-compose.yml up -d

docker-compose-prod: ## 🚀 Docker Compose для продакшена
	@echo "$(CYAN)🚀 Запуск Docker Compose (продакшен)...$(RESET)"
	@$(DOCKER_COMPOSE) -f docker/docker-compose.prod.yml up -d

docker-compose-down-dev: ## 🛑 Остановка разработки
	@echo "$(CYAN)🛑 Остановка Docker Compose (разработка)...$(RESET)"
	@$(DOCKER_COMPOSE) -f docker/docker-compose.yml down

docker-compose-down-prod: ## 🛑 Остановка продакшена
	@echo "$(CYAN)🛑 Остановка Docker Compose (продакшен)...$(RESET)"
	@$(DOCKER_COMPOSE) -f docker/docker-compose.prod.yml down

##@ 🧹 Очистка

clean: ## 🧹 Очистка временных файлов
	@echo "$(YELLOW)🧹 Очистка временных файлов...$(RESET)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name "*~" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache/ .coverage htmlcov/ .tox/ .mypy_cache/
	@echo "$(GREEN)✅ Временные файлы удалены$(RESET)"

clean-all: clean docker-clean ## 🧹 Полная очистка (включая Docker)
	@echo "$(YELLOW)🧹 Полная очистка завершена$(RESET)"

##@ 📊 Разработка

dev: docker-dev-up ## 🔧 Быстрый запуск среды разработки
	@echo "$(GREEN)🎉 Среда разработки запущена!$(RESET)"
	@echo "$(CYAN)📋 Доступные сервисы:$(RESET)"
	@echo "  $(WHITE)http://localhost:8000$(RESET)      - Основное приложение"
	@echo "  $(WHITE)http://localhost:8000/docs$(RESET) - Swagger UI"
	@echo "  $(WHITE)http://localhost:8080$(RESET)      - PgAdmin (tools profile)"
	@echo "  $(WHITE)http://localhost:8081$(RESET)      - Redis Commander (tools profile)"

dev-stop: docker-dev-down ## 🛑 Остановка среды разработки

prod: docker-prod-deploy ## 🚀 Быстрое развертывание продакшена
	@echo "$(GREEN)🎉 Продакшен развернут!$(RESET)"

##@ 📋 Информация

status: ## 📊 Общий статус проекта
	@echo "$(BLUE)📊 Статус проекта Avito AI Responder$(RESET)"
	@echo ""
	@echo "$(CYAN)🗂️ Файловая структура:$(RESET)"
	@ls -la
	@echo ""
	@echo "$(CYAN)🐳 Docker контейнеры:$(RESET)"
	@$(DOCKER) ps -a --filter "name=$(PROJECT_NAME)" 2>/dev/null || echo "Нет запущенных контейнеров"
	@echo ""
	@echo "$(CYAN)📊 Образы Docker:$(RESET)"
	@$(DOCKER) images | grep $(PROJECT_NAME) 2>/dev/null || echo "Образы не найдены"

logs: ## 📋 Показать логи приложения
	@echo "$(BLUE)📋 Логи приложения...$(RESET)"
	@$(PYTHON) scripts/docker_manager.py dev logs

shell: ## 🖥️ Подключиться к shell контейнера
	@echo "$(BLUE)🖥️ Подключение к shell...$(RESET)"
	@$(DOCKER_COMPOSE) -f docker/docker-compose.yml exec app /bin/bash

##@ 🎯 Полные циклы

full-setup: setup env install db-init ## 🎯 Полная настройка проекта
	@echo "$(GREEN)🎉 Полная настройка завершена!$(RESET)"
	@echo "$(YELLOW)⚠️ Не забудьте:$(RESET)"
	@echo "  1. Активировать виртуальное окружение: source venv/bin/activate"
	@echo "  2. Отредактировать .env файл с вашими API ключами"
	@echo "  3. Запустить: make dev"

full-test: code-quality test-coverage test-complete ## 🎯 Полное тестирование
	@echo "$(GREEN)🎉 Полное тестирование завершено!$(RESET)"

ci: code-quality test ## 🔄 CI/CD пайплайн (локальный)
	@echo "$(GREEN)🎉 CI проверки прошли успешно!$(RESET)"

##@ 🎨 Алиасы для удобства

up: dev ## 🚀 Алиас для dev
down: dev-stop ## 🛑 Алиас для dev-stop
build: docker-build ## 🏗️ Алиас для docker-build
deploy: prod ## 🚀 Алиас для prod

# Значения по умолчанию
.DEFAULT_GOAL := help