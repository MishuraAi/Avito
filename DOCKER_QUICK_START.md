# 🐳 Docker Quick Start Guide - Avito AI Responder

## 🚀 Быстрый старт (5 минут)

### 1. **Предварительные требования**
```bash
# Убедитесь что Docker установлен
docker --version
docker-compose --version

# Клонируйте репозиторий (если еще не сделали)
git clone <your-repo-url>
cd avito-ai-responder
```

### 2. **Настройка переменных окружения**
```bash
# Автоматическая настройка
python scripts/docker_manager.py setup

# ИЛИ вручную
cp .env.example .env

# Отредактируйте .env файл
nano .env
```

**Обязательно добавьте в .env:**
```env
GEMINI_API_KEY=your-gemini-api-key-here
AVITO_CLIENT_ID=your-avito-client-id
AVITO_CLIENT_SECRET=your-avito-client-secret
SECRET_KEY=your-super-secret-key-here
```

### 3. **Запуск среды разработки**
```bash
# Простой запуск
make dev

# ИЛИ через скрипт управления
python scripts/docker_manager.py dev up

# ИЛИ прямыми командами Docker
docker-compose -f docker/docker-compose.yml up -d
```

### 4. **Проверка работы**
```bash
# Проверка здоровья сервисов
make docker-health

# Просмотр логов
make logs

# Статус контейнеров
make status
```

### 5. **Доступ к приложению**
- 🌐 **Основное приложение**: http://localhost:8000
- 📚 **API документация**: http://localhost:8000/docs
- 🏥 **Health check**: http://localhost:8000/health

---

## 🎯 Основные команды

### 🔧 **Разработка**
```bash
make dev          # Запуск среды разработки
make dev-stop     # Остановка
make logs         # Просмотр логов
make shell        # Подключение к контейнеру
```

### 🚀 **Продакшен**
```bash
make prod         # Развертывание продакшена
make docker-prod-down  # Остановка продакшена
```

### 🛠️ **Управление**
```bash
make docker-build    # Сборка образа
make docker-clean    # Очистка ресурсов
make docker-health   # Проверка здоровья
```

---

## 📊 Доступные сервисы

### 🔧 **Основные сервисы**
| Сервис | URL | Описание |
|--------|-----|----------|
| FastAPI App | http://localhost:8000 | Основное приложение |
| Swagger UI | http://localhost:8000/docs | API документация |
| ReDoc | http://localhost:8000/redoc | Альтернативная документация |
| Health Check | http://localhost:8000/health | Проверка состояния |

### 🛠️ **Инструменты разработки** (с флагом `--profile tools`)
```bash
# Запуск с инструментами
docker-compose -f docker/docker-compose.yml --profile tools up -d
```

| Сервис | URL | Логин/Пароль | Описание |
|--------|-----|--------------|----------|
| PgAdmin | http://localhost:8080 | admin@avito-ai.local / admin123 | Управление PostgreSQL |
| Redis Commander | http://localhost:8081 | - | Просмотр Redis |

### 📊 **Мониторинг** (с флагом `--profile monitoring`)
```bash
# Запуск с мониторингом (только для продакшена)
docker-compose -f docker/docker-compose.prod.yml --profile monitoring up -d
```

| Сервис | URL | Описание |
|--------|-----|----------|
| Prometheus | http://localhost:9090 | Метрики |
| Grafana | http://localhost:3000 | Дашборды |

---

## 🗄️ Подключение к базе данных

### Через Docker:
```bash
# PostgreSQL
docker-compose -f docker/docker-compose.yml exec postgres psql -U avito_user -d avito_ai_db

# Redis
docker-compose -f docker/docker-compose.yml exec redis redis-cli
```

### Локально:
```bash
# PostgreSQL (если установлен локально)
psql -h localhost -p 5432 -U avito_user -d avito_ai_db

# Redis (если установлен локально) 
redis-cli -h localhost -p 6379
```

---

## 🔧 Продвинутые команды

### 📋 **Логирование и отладка**
```bash
# Логи конкретного сервиса
docker-compose -f docker/docker-compose.yml logs app
docker-compose -f docker/docker-compose.yml logs postgres
docker-compose -f docker/docker-compose.yml logs redis

# Следить за логами в реальном времени
docker-compose -f docker/docker-compose.yml logs -f app

# Информация о контейнерах
docker-compose -f docker/docker-compose.yml ps
docker stats
```

### 🛠️ **Работа с контейнерами**
```bash
# Выполнение команд в контейнере
docker-compose -f docker/docker-compose.yml exec app bash
docker-compose -f docker/docker-compose.yml exec app python scripts/check_database.py

# Перезапуск сервиса
docker-compose -f docker/docker-compose.yml restart app

# Пересборка и перезапуск
docker-compose -f docker/docker-compose.yml up -d --build app
```

### 🗄️ **Управление данными**
```bash
# Создание резервной копии БД
docker-compose -f docker/docker-compose.yml exec postgres pg_dump -U avito_user avito_ai_db > backup.sql

# Восстановление из резервной копии
cat backup.sql | docker-compose -f docker/docker-compose.yml exec -T postgres psql -U avito_user -d avito_ai_db

# Очистка volumes (ОСТОРОЖНО - удалит все данные!)
docker-compose -f docker/docker-compose.yml down -v
```

---

## 🚀 Продакшен развертывание

### 1. **Подготовка**
```bash
# Создайте продакшен .env файл
cp .env.example .env.prod

# Отредактируйте продакшен настройки
nano .env.prod
```

**Важные продакшен настройки:**
```env
ENVIRONMENT=production
DEBUG=False
DATABASE_URL=postgresql://user:strong_password@postgres:5432/avito_ai_db
SECRET_KEY=super-strong-secret-key-for-production
CORS_ORIGINS=https://yourdomain.com
```

### 2. **Развертывание**
```bash
# Сборка образа
make docker-build

# Развертывание продакшена
docker-compose -f docker/docker-compose.prod.yml up -d

# С мониторингом
docker-compose -f docker/docker-compose.prod.yml --profile monitoring up -d
```

### 3. **SSL сертификаты**
```bash
# Создайте директорию для SSL
mkdir -p docker/ssl

# Добавьте ваши сертификаты
cp your-cert.pem docker/ssl/cert.pem
cp your-key.pem docker/ssl/key.pem
```

---

## ❗ Решение проблем

### 🔧 **Частые проблемы**

#### Проблема: "Port already in use"
```bash
# Найти процесс использующий порт
sudo lsof -i :8000
sudo netstat -tulpn | grep :8000

# Остановить Docker контейнеры
docker-compose -f docker/docker-compose.yml down
```

#### Проблема: "Database connection failed"
```bash
# Проверить статус PostgreSQL
docker-compose -f docker/docker-compose.yml ps postgres

# Проверить логи PostgreSQL
docker-compose -f docker/docker-compose.yml logs postgres

# Перезапустить PostgreSQL
docker-compose -f docker/docker-compose.yml restart postgres
```

#### Проблема: "Migration failed"
```bash
# Подключиться к контейнеру
docker-compose -f docker/docker-compose.yml exec app bash

# Проверить миграции
python scripts/check_database.py
alembic current
alembic history

# Применить миграции вручную
alembic upgrade head
```

### 🧹 **Полная перезагрузка**
```bash
# Остановить все
docker-compose -f docker/docker-compose.yml down

# Удалить volumes (данные будут потеряны!)
docker-compose -f docker/docker-compose.yml down -v

# Очистить образы
docker image prune -f

# Пересоздать все
make docker-build
make dev
```

---

## 🎯 Проверочный чек-лист

### ✅ **Перед запуском убедитесь:**
- [ ] Docker и Docker Compose установлены
- [ ] Файл `.env` создан и настроен
- [ ] API ключи добавлены в `.env`
- [ ] Порты 8000, 5432, 6379 свободны

### ✅ **После запуска проверьте:**
- [ ] http://localhost:8000 открывается
- [ ] http://localhost:8000/docs показывает API документацию
- [ ] http://localhost:8000/health возвращает статус "healthy"
- [ ] `make docker-health` показывает все сервисы как работающие

### ✅ **Для продакшена дополнительно:**
- [ ] SSL сертификаты настроены
- [ ] Домен указывает на сервер
- [ ] Firewall настроен
- [ ] Мониторинг работает
- [ ] Резервное копирование настроено

---

## 📞 Поддержка

### 🛠️ **Полезные команды диагностики**
```bash
# Общая информация о системе
make status

# Здоровье сервисов
make docker-health

# Полные логи
make logs

# Информация о Docker
docker system info
docker system df
```

### 📋 **Логи для отправки в поддержку**
```bash
# Сохранить логи в файл
docker-compose -f docker/docker-compose.yml logs > docker-logs.txt

# Конфигурация системы
docker system info > system-info.txt

# Статус контейнеров
docker-compose -f docker/docker-compose.yml ps > containers-status.txt
```

---

**🎉 Поздравляем! Ваш Avito AI Responder готов к работе в Docker!**

> **💡 Совет**: Добавьте этот репозиторий в закладки и используйте команды `make help` для быстрого доступа ко всем возможностям.