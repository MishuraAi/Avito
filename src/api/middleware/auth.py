"""
Middleware для аутентификации JWT токенов.

Обрабатывает валидацию токенов для защищенных эндпоинтов
и добавляет информацию о пользователе в контекст запроса.
"""

import time
from typing import Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.database.session import get_db
from src.database.crud.users import user_crud, seller_crud

settings = get_settings()
security = HTTPBearer(auto_error=False)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware для автоматической аутентификации пользователей.
    
    Проверяет JWT токены в заголовке Authorization и добавляет
    информацию о пользователе в state запроса.
    """
    
    # Публичные эндпоинты, не требующие аутентификации
    PUBLIC_PATHS = {
        "/",
        "/docs",
        "/redoc", 
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register/user",
        "/api/v1/auth/register/seller",
        "/api/v1/auth/reset-password",
        "/api/v1/auth/verify-email",
        "/api/v1/system/health",
        "/api/v1/system/info"
    }
    
    async def dispatch(self, request: Request, call_next):
        """
        Основной метод middleware для обработки запросов.
        """
        start_time = time.time()
        
        # Проверяем, требует ли эндпоинт аутентификации
        if self._is_public_path(request.url.path):
            response = await call_next(request)
            self._add_timing_header(response, start_time)
            return response
        
        # Извлекаем токен из заголовка
        token = self._extract_token(request)
        
        if not token:
            return self._unauthorized_response("Токен аутентификации не предоставлен")
        
        # Валидируем токен и получаем пользователя
        user, error = await self._validate_token_and_get_user(token, request)
        
        if error:
            return self._unauthorized_response(error)
        
        if user:
            # Добавляем пользователя в state запроса
            request.state.current_user = user
            request.state.user_type = "seller" if hasattr(user, "company_name") else "user"
        
        response = await call_next(request)
        self._add_timing_header(response, start_time)
        return response
    
    def _is_public_path(self, path: str) -> bool:
        """Проверяет, является ли путь публичным."""
        return path in self.PUBLIC_PATHS or path.startswith("/static/")
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """Извлекает JWT токен из заголовка Authorization."""
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None
        
        if not authorization.startswith("Bearer "):
            return None
        
        return authorization.split(" ")[1]
    
    async def _validate_token_and_get_user(self, token: str, request: Request) -> tuple[Optional[object], Optional[str]]:
        """
        Валидирует JWT токен и возвращает пользователя.
        
        Returns:
            tuple: (user_object, error_message)
        """
        try:
            # Декодируем токен
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET_KEY, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            user_id = payload.get("sub")
            user_type = payload.get("type")
            
            if not user_id or not user_type:
                return None, "Недействительный токен"
            
            # Получаем пользователя из базы данных
            db: Session = next(get_db())
            try:
                if user_type == "user":
                    user = user_crud.get(db, id=user_id)
                elif user_type == "seller":
                    user = seller_crud.get(db, id=user_id)
                else:
                    return None, "Неизвестный тип пользователя"
                
                if not user:
                    return None, "Пользователь не найден"
                
                if not user.is_active:
                    return None, "Аккаунт деактивирован"
                
                return user, None
                
            finally:
                db.close()
                
        except JWTError:
            return None, "Недействительный токен"
        except Exception as e:
            return None, f"Ошибка аутентификации: {str(e)}"
    
    def _unauthorized_response(self, detail: str) -> Response:
        """Возвращает ответ об ошибке аутентификации."""
        return Response(
            content=f'{{"detail": "{detail}"}}',
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={
                "WWW-Authenticate": "Bearer",
                "Content-Type": "application/json"
            }
        )
    
    def _add_timing_header(self, response: Response, start_time: float) -> None:
        """Добавляет заголовок с временем обработки запроса."""
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)