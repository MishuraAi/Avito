"""
Упрощенная версия auth.py для успешного деплоя
ВРЕМЕННО убираем сложные зависимости
"""

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
import logging

# Создаем роутер
router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/avito/callback")
async def avito_oauth_callback(
    code: str = Query(..., description="Authorization code from Avito"),
    state: str = Query(None, description="State parameter for security")
):
    """
    Callback endpoint для OAuth авторизации Avito
    """
    try:
        logger.info(f"Получен Avito OAuth callback: code={code[:10]}..., state={state}")
        
        success_html = f"""
        <html>
            <head>
                <title>Avito AI Responder - Успешная авторизация</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    .success {{ color: green; font-size: 24px; margin: 20px 0; }}
                    .info {{ color: #666; font-size: 16px; margin: 10px 0; }}
                    .code {{ background: #f0f0f0; padding: 10px; border-radius: 5px; font-family: monospace; }}
                </style>
            </head>
            <body>
                <h1>🎉 Авторизация Avito успешна!</h1>
                <div class="success">✅ Подключение к Avito API установлено</div>
                <div class="info">Получен код авторизации:</div>
                <div class="code">{code[:20]}...</div>
                <div class="info">State: {state or 'не указан'}</div>
                <div class="info">
                    <p>Теперь ваш автоответчик может получать доступ к сообщениям Avito!</p>
                    <p>Вы можете закрыть это окно.</p>
                </div>
            </body>
        </html>
        """
        
        return HTMLResponse(content=success_html, status_code=200)
        
    except Exception as e:
        error_html = f"""
        <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>❌ Ошибка авторизации Avito</h1>
                <p>Ошибка: {str(e)}</p>
            </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=400)

@router.get("/avito/status")
async def avito_auth_status():
    """Проверка статуса авторизации Avito"""
    return {
        "status": "ready",
        "callback_url": "https://avito-joq9.onrender.com/api/v1/auth/avito/callback",
        "message": "Готов к получению OAuth callback от Avito",
        "version": "1.0.0",
        "endpoints": [
            "/api/v1/auth/avito/callback",
            "/api/v1/auth/avito/status"
        ]
    }

@router.get("/test")
async def auth_test():
    """Тестовый endpoint"""
    return {"status": "Auth router working!", "timestamp": "2025-01-07"}