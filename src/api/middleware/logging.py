"""
Middleware для логирования HTTP запросов.

Записывает детальную информацию о всех входящих запросах
и ответах для мониторинга и отладки.
"""

import time
import logging
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

from src.core.config import get_settings

settings = get_settings()

# Настройка логгера для HTTP запросов
logger = logging.getLogger("avito_ai.api")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для логирования всех HTTP запросов и ответов.
    
    Записывает информацию о методе, URL, заголовках, времени обработки,
    статусе ответа и размере данных.
    """
    
    # Эндпоинты, которые не нужно логировать подробно
    SKIP_DETAILED_LOGGING = {
        "/api/v1/system/health",
        "/docs",
        "/redoc",
        "/openapi.json"
    }
    
    # Заголовки, которые не должны попадать в логи (содержат чувствительные данные)
    SENSITIVE_HEADERS = {
        "authorization",
        "cookie",
        "x-api-key",
        "x-auth-token"
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Основной метод middleware для логирования запросов.
        """
        start_time = time.time()
        
        # Логируем входящий запрос
        await self._log_request(request, start_time)
        
        # Обрабатываем запрос
        response = await call_next(request)
        
        # Логируем ответ
        process_time = time.time() - start_time
        await self._log_response(request, response, process_time)
        
        return response
    
    async def _log_request(self, request: Request, start_time: float) -> None:
        """Логирует входящий HTTP запрос."""
        # Базовая информация о запросе
        log_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(start_time)),
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
        }
        
        # Добавляем информацию о пользователе, если доступна
        if hasattr(request.state, "current_user") and request.state.current_user:
            log_data["user_id"] = str(request.state.current_user.id)
            log_data["user_type"] = getattr(request.state, "user_type", "unknown")
        
        # Детальное логирование только для важных эндпоинтов
        if request.url.path not in self.SKIP_DETAILED_LOGGING:
            log_data["headers"] = self._filter_sensitive_headers(dict(request.headers))
            
            # Логируем тело запроса для POST/PUT/PATCH
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await self._get_request_body(request)
                    if body:
                        log_data["body_size"] = len(body)
                        # Логируем JSON данные (без чувствительной информации)
                        if request.headers.get("content-type", "").startswith("application/json"):
                            try:
                                json_data = json.loads(body.decode())
                                log_data["json_data"] = self._filter_sensitive_json(json_data)
                            except (json.JSONDecodeError, UnicodeDecodeError):
                                pass
                except Exception as e:
                    log_data["body_read_error"] = str(e)
        
        # Записываем лог
        logger.info(f"REQUEST: {request.method} {request.url.path}", extra={"request_data": log_data})
    
    async def _log_response(self, request: Request, response: Response, process_time: float) -> None:
        """Логирует HTTP ответ."""
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2),
            "response_size": self._get_response_size(response),
        }
        
        # Добавляем информацию о пользователе
        if hasattr(request.state, "current_user") and request.state.current_user:
            log_data["user_id"] = str(request.state.current_user.id)
        
        # Детальное логирование для ошибок
        if response.status_code >= 400:
            log_data["headers"] = dict(response.headers)
            
            # Пытаемся получить тело ответа для ошибок
            if hasattr(response, "body"):
                try:
                    log_data["response_body"] = response.body.decode()
                except (UnicodeDecodeError, AttributeError):
                    pass
        
        # Выбираем уровень логирования
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO
        
        logger.log(
            log_level,
            f"RESPONSE: {response.status_code} {request.method} {request.url.path} ({process_time*1000:.2f}ms)",
            extra={"response_data": log_data}
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """Получает IP адрес клиента с учетом прокси."""
        # Проверяем заголовки прокси
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Возвращаем прямой IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _filter_sensitive_headers(self, headers: dict) -> dict:
        """Фильтрует чувствительные заголовки из логов."""
        filtered = {}
        for key, value in headers.items():
            if key.lower() in self.SENSITIVE_HEADERS:
                filtered[key] = "[FILTERED]"
            else:
                filtered[key] = value
        return filtered
    
    def _filter_sensitive_json(self, data: dict) -> dict:
        """Фильтрует чувствительные данные из JSON."""
        sensitive_fields = {"password", "token", "secret", "key", "api_key"}
        
        if isinstance(data, dict):
            filtered = {}
            for key, value in data.items():
                if key.lower() in sensitive_fields:
                    filtered[key] = "[FILTERED]"
                elif isinstance(value, dict):
                    filtered[key] = self._filter_sensitive_json(value)
                else:
                    filtered[key] = value
            return filtered
        
        return data
    
    async def _get_request_body(self, request: Request) -> bytes:
        """Получает тело запроса для логирования."""
        try:
            return await request.body()
        except Exception:
            return b""
    
    def _get_response_size(self, response: Response) -> int:
        """Получает размер ответа в байтах."""
        if hasattr(response, "body") and response.body:
            return len(response.body)
        
        if isinstance(response, StreamingResponse):
            return 0  # Размер streaming ответа неизвестен
        
        # Пытаемся получить из заголовка
        content_length = response.headers.get("content-length")
        if content_length:
            try:
                return int(content_length)
            except ValueError:
                pass
        
        return 0