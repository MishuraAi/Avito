# 🐳 Dockerfile для Avito AI Responder
# Оптимизирован для продакшен использования

# Используем официальный Python образ
FROM python:3.11-slim as base

# Метаданные образа
LABEL maintainer="Avito AI Team"
LABEL version="0.1.0-beta"
LABEL description="Avito AI Responder - умный автоответчик для Авито"

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    # Основные утилиты
    curl \
    wget \
    git \
    # Для компиляции Python пакетов
    gcc \
    g++ \
    # Для psycopg2
    libpq-dev \
    # Для работы с изображениями (Pillow)
    libjpeg-dev \
    libpng-dev \
    # Очистка кеша
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя приложения (безопасность)
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Установка рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt requirements-dev.txt ./

# Установка Python зависимостей
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Создание директорий для данных
RUN mkdir -p /app/data/logs /app/data/uploads /app/data/cache && \
    chown -R appuser:appuser /app/data

# Копирование исходного кода
COPY . .

# Установка прав доступа
RUN chown -R appuser:appuser /app

# Переключение на пользователя приложения
USER appuser

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Порт приложения
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Команда запуска (для продакшена)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# 🔧 Multi-stage build для разработки
FROM base as development

# Переключаемся обратно на root для установки dev зависимостей
USER root

# Установка дополнительных dev зависимостей
RUN pip install --no-cache-dir -r requirements-dev.txt

# Возвращаемся к пользователю приложения
USER appuser

# Команда для разработки с hot reload
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]

# 🚀 Production stage
FROM base as production

# Дополнительные оптимизации для продакшена
ENV ENVIRONMENT=production
ENV DEBUG=false

# Команда запуска с gunicorn для лучшей производительности
CMD ["gunicorn", "src.api.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"] 