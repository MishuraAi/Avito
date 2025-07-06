"""
Middleware для ограничения частоты запросов (Rate Limiting).

Защищает API от злоупотреблений и DDoS атак путем ограничения
количества запросов с одного IP или от одного пользователя.
"""

import time
import json
from typing import Dict, Optional
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict, deque

from src.core.config import get_settings

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware для ограничения частоты запросов.
    
    Использует алгоритм sliding window для точного подсчета запросов
    и поддерживает разные лимиты для разных типов пользователей.
    """
    
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        
        # Хранилище для отслеживания запросов (в памяти)
        # В продакшене стоит заменить на Redis
        self.request_counts: Dict[str, deque] = defaultdict(deque)
        
        # Настройки лимитов по умолчанию
        self.default_limits = {
            "anonymous": {"requests": 100, "window": 3600},  # 100 запросов в час для анонимов
            "user": {"requests": 1000, "window": 3600},      # 1000 запросов в час для пользователей
            "seller_basic": {"requests": 5000, "window": 3600},    # 5000 запросов в час для basic
            "seller_pro": {"requests": 20000, "window": 3600},     # 20000 запросов в час для pro
            "seller_enterprise": {"requests": 100000, "window": 3600}, # 100000 запросов в час для enterprise
        }
        
        # Особые лимиты для отдельных эндпоинтов
        self.endpoint_limits = {
            "/api/v1/auth/login": {"requests": 10, "window": 900},  # 10 попыток входа за 15 минут
            "/api/v1/auth/register/user": {"requests": 5, "window": 3600},  # 5 регистраций в час
            "/api/v1/auth/register/seller": {"requests": 3, "window": 3600}, # 3 регистрации в час
            "/api/v1/messages/auto-reply": {"requests": 100, "window": 3600}, # 100 автоответов в час
        }
        
        # Белый список IP (для внутренних сервисов)
        self.whitelist_ips = {
            "127.0.0.1",
            "::1",
            "10.0.0.0/8",  # Внутренние сети
        }
    
    async def dispatch(self, request: Request, call_next):
        """
        Основной метод middleware для проверки лимитов.
        """
        client_ip = self._get_client_ip(request)
        
        # Пропускаем проверку для IP из белого списка
        if self._is_whitelisted(client_ip):
            return await call_next(request)
        
        # Определяем ключ для rate limiting
        rate_limit_key = self._get_rate_limit_key(request, client_ip)
        
        # Получаем лимиты для данного запроса
        limits = self._get_limits_for_request(request)
        
        # Проверяем лимиты
        if not self._check_rate_limit(rate_limit_key, limits, request.url.path):
            return self._rate_limit_exceeded_response(limits)
        
        # Регистрируем запрос
        self._record_request(rate_limit_key, request.url.path)
        
        response = await call_next(request)
        
        # Добавляем заголовки с информацией о лимитах
        self._add_rate_limit_headers(response, rate_limit_key, limits, request.url.path)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Получает IP адрес клиента."""
        # Проверяем заголовки прокси
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _is_whitelisted(self, ip: str) -> bool:
        """Проверяет, находится ли IP в белом списке."""
        return ip in self.whitelist_ips
    
    def _get_rate_limit_key(self, request: Request, client_ip: str) -> str:
        """Определяет ключ для rate limiting."""
        # Если пользователь аутентифицирован, используем его ID
        if hasattr(request.state, "current_user") and request.state.current_user:
            user_id = str(request.state.current_user.id)
            user_type = getattr(request.state, "user_type", "user")
            return f"user:{user_type}:{user_id}"
        
        # Для анонимных пользователей используем IP
        return f"ip:{client_ip}"
    
    def _get_limits_for_request(self, request: Request) -> Dict[str, int]:
        """Получает лимиты для конкретного запроса."""
        # Проверяем особые лимиты для эндпоинта
        if request.url.path in self.endpoint_limits:
            return self.endpoint_limits[request.url.path]
        
        # Определяем тип пользователя
        if hasattr(request.state, "current_user") and request.state.current_user:
            user = request.state.current_user
            user_type = getattr(request.state, "user_type", "user")
            
            if user_type == "seller":
                # Для продавцов лимиты зависят от подписки
                subscription_plan = getattr(user, "subscription_plan", "basic")
                limit_key = f"seller_{subscription_plan}"
                return self.default_limits.get(limit_key, self.default_limits["seller_basic"])
            else:
                return self.default_limits["user"]
        
        # Для анонимных пользователей
        return self.default_limits["anonymous"]
    
    def _check_rate_limit(self, key: str, limits: Dict[str, int], endpoint: str) -> bool:
        """Проверяет, не превышен ли лимит запросов."""
        current_time = time.time()
        window_start = current_time - limits["window"]
        
        # Получаем очередь запросов для данного ключа
        requests = self.request_counts[key]
        
        # Очищаем старые запросы (вне окна)
        while requests and requests[0] < window_start:
            requests.popleft()
        
        # Проверяем, превышен ли лимит
        return len(requests) < limits["requests"]
    
    def _record_request(self, key: str, endpoint: str) -> None:
        """Регистрирует новый запрос."""
        current_time = time.time()
        self.request_counts[key].append(current_time)
    
    def _add_rate_limit_headers(self, response: Response, key: str, limits: Dict[str, int], endpoint: str) -> None:
        """Добавляет заголовки с информацией о лимитах."""
        current_time = time.time()
        window_start = current_time - limits["window"]
        
        # Получаем актуальное количество запросов
        requests = self.request_counts[key]
        while requests and requests[0] < window_start:
            requests.popleft()
        
        used_requests = len(requests)
        remaining_requests = max(0, limits["requests"] - used_requests)
        
        # Время до сброса окна
        if requests:
            reset_time = int(requests[0] + limits["window"])
        else:
            reset_time = int(current_time + limits["window"])
        
        response.headers["X-RateLimit-Limit"] = str(limits["requests"])
        response.headers["X-RateLimit-Remaining"] = str(remaining_requests)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        response.headers["X-RateLimit-Window"] = str(limits["window"])
    
    def _rate_limit_exceeded_response(self, limits: Dict[str, int]) -> Response:
        """Возвращает ответ при превышении лимита."""
        error_response = {
            "detail": "Превышен лимит запросов",
            "error_code": "RATE_LIMIT_EXCEEDED",
            "limit": limits["requests"],
            "window_seconds": limits["window"],
            "retry_after": limits["window"]
        }
        
        return Response(
            content=json.dumps(error_response),
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={
                "Content-Type": "application/json",
                "Retry-After": str(limits["window"]),
                "X-RateLimit-Limit": str(limits["requests"]),
                "X-RateLimit-Remaining": "0",
            }
        )