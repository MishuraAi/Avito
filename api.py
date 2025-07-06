"""
Основной модуль FastAPI приложения МИШУРА Style Bot.
Содержит все API endpoints и бизнес-логику.
"""

import os
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
import uvicorn
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание FastAPI приложения
app = FastAPI(
    title="МИШУРА Style Bot API",
    description="Персональный ИИ-стилист для Telegram",
    version="6.1.0"
)

# Подключение статических файлов, если папка существует
webapp_dir = Path("webapp")
if webapp_dir.exists() and webapp_dir.is_dir():
    app.mount("/webapp", StaticFiles(directory="webapp"), name="webapp")
else:
    logger.warning("Директория 'webapp' не найдена. Статические файлы не будут доступны.")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Проверка состояния сервиса"""
    return {
        "status": "healthy",
        "service": "mishura-bot",
        "version": "6.1.0"
    }

# Root endpoint
@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "message": "МИШУРА Style Bot API",
        "status": "running",
        "webapp": "/webapp/" if webapp_dir.exists() else None
    }

# Webhook endpoint для Telegram
@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Обработка Telegram webhook"""
    try:
        body = await request.body()
        logger.info("Received webhook: %s", body)
        # TODO: Реализовать обработку webhook
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

# Запуск для локальной разработки
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Включен reload для разработки
        log_level="debug"
    ) 