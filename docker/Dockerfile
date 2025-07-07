# 🐳 Dockerfile для Avito AI Responder
# Оптимизированный образ для продакшена

# ==============================================================================
# 🏗️ СТАДИЯ 1: Build стадия (установка зависимостей)
# ==============================================================================
FROM python:3.11-slim as builder

# Установка системных зависимостей для сборки
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя приложения
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Установка Poetry для управления зависимостями
RUN pip install --no-cache-dir poetry==1.6.1

# Настройка Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Создание рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY pyproject.toml poetry.lock* requirements.txt requirements-dev.txt ./

# Установка зависимостей через pip (альтернатива Poetry если нет pyproject.toml)
RUN pip install --no-cache-dir -r requirements.txt \
    && rm -rf /tmp/pip-*

# ==============================================================================
# 🚀 СТАДИЯ 2: Runtime стадия (финальный образ)
# ==============================================================================
FROM python:3.11-slim as runtime

# Установка runtime зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя приложения
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Создание директорий приложения
RUN mkdir -p /app /app/data /app/logs \
    && chown -R appuser:appuser /app

# Установка рабочей директории
WORKDIR /app

# Копирование установленных зависимостей из builder стадии
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Копирование исходного кода приложения
COPY --chown=appuser:appuser . .

# Настройка переменных окружения
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    PORT=8000

# Создание директории для логов и данных
RUN mkdir -p /app/data/logs /app/data/cache \
    && chown -R appuser:appuser /app/data

# Переключение на пользователя приложения
USER appuser

# Expose порт приложения
EXPOSE 8000

# Health check для контейнера
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Команда запуска по умолчанию
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

# ==============================================================================
# 📋 МЕТАДАННЫЕ ОБРАЗА
# ==============================================================================
LABEL maintainer="Avito AI Responder Team" \
      version="0.1.0" \
      description="Умный автоответчик для Авито с ИИ-консультантом" \
      org.opencontainers.image.source="https://github.com/your-username/avito-ai-responder"